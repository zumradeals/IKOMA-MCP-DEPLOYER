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

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

# --- Constantes (Top-level, utilisées par d'autres modules) ---
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
REPOS_DIR = DATA_DIR / "repos"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "ikoma.db"
RELEASE_FILE = "ikoma.release.json"
DEFAULT_HEALTH_TIMEOUT = 60  # secondes
DEFAULT_HEALTH_INTERVAL = 2  # secondes
DEFAULT_EXPECTED_STATUS = 200


# --- Exceptions et Dataclasses (Top-level, utilisées par d'autres modules) ---
class DeployError(Exception):
    """Erreur fonctionnelle lors d'un déploiement."""


@dataclass
class ReleaseConfig:
    compose_file: Path
    services: List[str]
    health: Dict[str, object]


# --- API Publique (verrouillée) ---
def deploy_up(app_id: str, ref: str) -> None:
    """Déploie une application unique via Docker Compose.

    Args:
        app_id: Identifiant applicatif utilisé pour nommer les dossiers et les entrées DB.
        ref: Référence Git à déployer (branch, tag ou commit SHA).

    Raises:
        DeployError: en cas d'échec (le statut SQLite est quand même mis à jour).
    """
    # Imports lazy pour éviter les imports circulaires
    from core.deploy.compose import compose_up
    from core.deploy.health import wait_for_health
    from core.deploy.preflight import ensure_directories, load_release_config, preflight_environment, preflight_release
    from core.logging.logger import build_logger
    from core.scm.git_repo import sync_repository
    from core.store.sqlite_store import DeploymentState

    logger = None
    db = None
    repo_dir = None
    release_config = None

    try:
        # 1. Initialisation et Pré-vol
        logger = build_logger(app_id, LOGS_DIR)
        logger.info("=== Déploiement %s (%s) démarré ===", app_id, ref)

        ensure_directories(DATA_DIR, REPOS_DIR, LOGS_DIR)
        preflight_environment(logger)

        # 2. Synchronisation Git
        repo_dir = sync_repository(app_id, ref, REPOS_DIR, logger)

        # 3. Chargement de la configuration
        release_config = load_release_config(repo_dir, RELEASE_FILE)
        preflight_release(release_config, logger)

        # 4. Déploiement Docker Compose
        compose_up(release_config, repo_dir, logger)

        # 5. Vérification de santé
        wait_for_health(release_config.health, logger)

        # 6. Mise à jour du statut SQLite (Succès)
        db = DeploymentState(DB_PATH)
        db.ensure_schema()
        db.upsert_status(app_id, ref, "HEALTHY", "Déploiement validé par healthcheck")
        logger.info("=== Déploiement %s (%s) terminé avec succès ===", app_id, ref)

    except DeployError as exc:
        # Erreur fonctionnelle déjà tracée et gérée
        message = f"Déploiement échoué: {exc}"
        if logger:
            logger.exception(message)
        
        # Tentative de mise à jour du statut FAILED
        if db is None:
            try:
                db = DeploymentState(DB_PATH)
                db.ensure_schema()
            except Exception as db_init_exc:
                if logger:
                    logger.error("Impossible d'initialiser la DB pour tracer l'échec: %s", db_init_exc)
        
        if db is not None:
            try:
                db.upsert_status(app_id, ref, "FAILED", str(exc))
            except Exception as db_exc:
                if logger:
                    logger.error("Impossible d'écrire le statut d'échec: %s", db_exc)
        
        raise DeployError(message) from exc

    except Exception as exc:
        # Erreur non prévue (ex: NameError due à un import manquant, FileNotFoundError, etc.)
        message = f"Erreur critique lors du déploiement: {exc}"
        if logger:
            logger.exception(message)
        
        # Tentative de mise à jour du statut FAILED
        if db is None:
            try:
                db = DeploymentState(DB_PATH)
                db.ensure_schema()
            except Exception as db_init_exc:
                if logger:
                    logger.error("Impossible d'initialiser la DB pour tracer l'échec: %s", db_init_exc)
        
        if db is not None:
            try:
                db.upsert_status(app_id, ref, "FAILED", message)
            except Exception as db_exc:
                if logger:
                    logger.error("Impossible d'écrire le statut d'échec: %s", db_exc)
        
        raise DeployError(message) from exc
