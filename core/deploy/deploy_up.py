"""Flux minimal de déploiement avec Docker Compose.

Ce module implémente un chemin unique et simple :
- synchronisation d'un dépôt applicatif (clone ou fetch + checkout du ref)
- lecture du manifest `ikoma.release.json`
- exécution d'un `docker compose up -d`
- healthcheck HTTP pour valider le déploiement
- journalisation dans `data/logs/<app_id>/deploy.log`
- mise à jour du statut dans SQLite (`HEALTHY` ou `FAILED`)

Le code est volontairement lisible et peu magique pour faciliter les
prochaines itérations.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
REPOS_DIR = DATA_DIR / "repos"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "state.sqlite"
RELEASE_FILE = "ikoma.release.json"
DEFAULT_HEALTH_TIMEOUT = 60  # secondes
DEFAULT_HEALTH_INTERVAL = 2  # secondes
DEFAULT_EXPECTED_STATUS = 200


class DeployError(Exception):
    """Erreur fonctionnelle lors d'un déploiement."""


@dataclass
class ReleaseConfig:
    compose_file: Path
    services: List[str]
    health: Dict[str, object]


def deploy_up(app_id: str, ref: str) -> None:
    """Déploie une application unique via Docker Compose.

    Args:
        app_id: Identifiant applicatif utilisé pour nommer les dossiers et les entrées DB.
        ref: Référence Git à déployer (branch, tag ou commit SHA).

    Raises:
        DeployError: en cas d'échec (le statut SQLite est quand même mis à jour).
    """

    logger = _build_logger(app_id)
    logger.info("=== Déploiement %s (%s) démarré ===", app_id, ref)

    db = _DeploymentState(DB_PATH)
    db.ensure_schema()

    try:
        repo_dir = _sync_repository(app_id, ref, logger)
        release = _load_release_config(repo_dir)
        _compose_up(release, repo_dir, logger)
        _wait_for_health(release.health, logger)
    except Exception as exc:  # noqa: BLE001 - capture volontaire pour tracer l'échec
        message = f"deploy_up échoué: {exc}"
        logger.exception(message)
        db.upsert_status(app_id, ref, "FAILED", message)
        raise DeployError(message) from exc

    db.upsert_status(app_id, ref, "HEALTHY", "Déploiement validé par healthcheck")
    logger.info("=== Déploiement %s (%s) terminé avec succès ===", app_id, ref)


def _build_logger(app_id: str) -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    app_log_dir = LOGS_DIR / app_id
    app_log_dir.mkdir(parents=True, exist_ok=True)
    log_file = app_log_dir / "deploy.log"

    logger = logging.getLogger(f"deploy.{app_id}")
    logger.setLevel(logging.INFO)

    if not any(isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_file) for handler in logger.handlers):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


class _DeploymentState:
    """Petit helper pour stocker l'état dans SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deployments (
                    app_id TEXT PRIMARY KEY,
                    ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message TEXT
                )
                """
            )

    def upsert_status(self, app_id: str, ref: str, status: str, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO deployments(app_id, ref, status, updated_at, message)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO UPDATE SET
                    ref=excluded.ref,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    message=excluded.message
                """,
                (app_id, ref, status, timestamp, message),
            )


def _sync_repository(app_id: str, ref: str, logger: logging.Logger) -> Path:
    """Clone ou met à jour le dépôt applicatif."""

    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    repo_dir = REPOS_DIR / app_id
    remote_url = os.getenv("IKOMA_GIT_REMOTE")

    if repo_dir.exists():
        logger.info("Repo %s déjà présent, fetch + checkout", repo_dir)
        _run(["git", "fetch", "--all", "--prune"], cwd=repo_dir, logger=logger)
        _run(["git", "checkout", ref], cwd=repo_dir, logger=logger)
        _run(["git", "pull", "--ff-only"], cwd=repo_dir, logger=logger)
    else:
        if not remote_url:
            raise DeployError(
                "Impossible de cloner : définir la variable d'environnement IKOMA_GIT_REMOTE",
            )
        logger.info("Clonage de %s dans %s", remote_url, repo_dir)
        _run(["git", "clone", remote_url, str(repo_dir)], logger=logger)
        _run(["git", "checkout", ref], cwd=repo_dir, logger=logger)

    return repo_dir


def _load_release_config(repo_dir: Path) -> ReleaseConfig:
    release_path = repo_dir / RELEASE_FILE
    if not release_path.exists():
        raise DeployError(f"Manifest {RELEASE_FILE} introuvable dans {repo_dir}")

    with release_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    compose_file = repo_dir / payload.get("compose_file", "docker-compose.yml")
    services = list(payload.get("services", []))
    health = dict(payload.get("health", {}))

    if not compose_file.exists():
        raise DeployError(f"Fichier compose introuvable: {compose_file}")
    if not health.get("url"):
        raise DeployError("Le healthcheck HTTP doit définir une clé 'url'")

    return ReleaseConfig(compose_file=compose_file, services=services, health=health)


def _compose_up(release: ReleaseConfig, repo_dir: Path, logger: logging.Logger) -> None:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(release.compose_file),
        "up",
        "-d",
    ]
    if release.services:
        cmd.extend(release.services)

    logger.info("Exécution: %s", " ".join(cmd))
    _run(cmd, cwd=repo_dir, logger=logger)


def _wait_for_health(health: Dict[str, object], logger: logging.Logger) -> None:
    url = str(health.get("url"))
    expected_status = int(health.get("expected_status", DEFAULT_EXPECTED_STATUS))
    timeout = int(health.get("timeout", DEFAULT_HEALTH_TIMEOUT))
    interval = int(health.get("interval", DEFAULT_HEALTH_INTERVAL))

    logger.info(
        "Healthcheck HTTP sur %s (attendu=%s, timeout=%ss, interval=%ss)",
        url,
        expected_status,
        timeout,
        interval,
    )

    deadline = time.time() + timeout
    last_error: str | None = None

    while time.time() < deadline:
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=interval) as resp:  # nosec - URL contrôlée via manifest
                if resp.status == expected_status:
                    logger.info("Healthcheck OK (%s)", resp.status)
                    return
                last_error = f"Statut inattendu: {resp.status}"
                logger.warning(last_error)
        except (HTTPError, URLError) as exc:
            last_error = f"Erreur HTTP: {exc}"
            logger.warning(last_error)
        except Exception as exc:  # noqa: BLE001
            last_error = f"Erreur non prévue: {exc}"
            logger.warning(last_error)

        time.sleep(interval)

    raise DeployError(last_error or "Healthcheck expiré")


def _run(command: List[str], logger: logging.Logger, cwd: Path | None = None) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    logger.info("$ %s", " ".join(command))
    if result.stdout:
        logger.info(result.stdout.strip())

    if result.returncode != 0:
        raise DeployError(f"Commande échouée ({result.returncode}): {' '.join(command)}")
