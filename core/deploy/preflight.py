from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict

from core.deploy.deploy_up import DeployError, ReleaseConfig
from core.logging.logger import run_command


def preflight_environment(logger) -> None:
    """Vérifie la présence des dépendances indispensables."""

    for binary in ("docker",):
        if not shutil.which(binary):
            raise DeployError(f"Binaire requis introuvable: {binary}")

    run_command(["docker", "--version"], logger=logger)
    run_command(["docker", "compose", "version"], logger=logger)


def ensure_directories(*directories: Path) -> None:
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def load_release_config(repo_dir: Path, release_file: str) -> ReleaseConfig:
    release_path = repo_dir / release_file
    if not release_path.exists():
        raise DeployError(f"Manifest {release_file} introuvable dans {repo_dir}")

    try:
        with release_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:  # noqa: B904 - message métier
        raise DeployError(f"Manifest {release_file} invalide: {exc}") from exc

    _validate_release_payload(payload, release_path)

    compose_file = repo_dir / payload.get("compose_file", "docker-compose.yml")
    services = list(payload.get("services", []))
    health = dict(payload.get("health", {}))

    return ReleaseConfig(compose_file=compose_file, services=services, health=health)


def preflight_release(release: ReleaseConfig, logger) -> None:
    if not release.compose_file.exists():
        raise DeployError(f"Fichier compose introuvable: {release.compose_file}")
    if not os.access(release.compose_file, os.R_OK):
        raise DeployError(f"Fichier compose illisible: {release.compose_file}")

    services_list = ", ".join(release.services) if release.services else "tous"
    logger.info(
        "Manifest validé: compose=%s, services=%s, health=%s",
        release.compose_file,
        services_list,
        release.health,
    )


def _validate_release_payload(payload: Dict[str, object], release_path: Path) -> None:
    if not isinstance(payload, dict):
        raise DeployError(f"Manifest {release_path} doit être un objet JSON")

    compose_file = payload.get("compose_file", "docker-compose.yml")
    if not isinstance(compose_file, str) or not compose_file.strip():
        raise DeployError("La clé 'compose_file' doit être une chaîne non vide")

    services = payload.get("services", [])
    if not isinstance(services, list) or not all(isinstance(s, str) and s for s in services):
        raise DeployError("La clé 'services' doit être une liste de chaînes")

    health = payload.get("health")
    if not isinstance(health, dict):
        raise DeployError("La clé 'health' doit être un objet JSON")

    if not isinstance(health.get("url"), str) or not health.get("url"):
        raise DeployError("Le healthcheck HTTP doit définir une clé 'url' non vide")

    for numeric_key in ("expected_status", "timeout", "interval", "retries"):
        if numeric_key in health and not isinstance(health[numeric_key], (int, float)):
            raise DeployError(f"health.{numeric_key} doit être un nombre si présent")

    if "interval" in health and health["interval"] <= 0:
        raise DeployError("health.interval doit être strictement positif")
    if "timeout" in health and health["timeout"] <= 0:
        raise DeployError("health.timeout doit être strictement positif")
    if "retries" in health and health["retries"] <= 0:
        raise DeployError("health.retries doit être strictement positif")
