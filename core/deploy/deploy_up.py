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

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
REPOS_DIR = DATA_DIR / "repos"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "ikoma.db"
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

    logger = build_logger(app_id, LOGS_DIR)
    logger.info("=== Déploiement %s (%s) démarré ===", app_id, ref)


    except Exception as exc:  # noqa: BLE001 - capture volontaire pour tracer l'échec
        message = f"deploy_up échoué: {exc}"
        logger.exception(message)
        if db is not None:
            try:
                db.upsert_status(app_id, ref, "FAILED", message)
            except Exception as db_exc:  # noqa: BLE001 - traçage secondaire
                logger.exception("Impossible d'écrire le statut d'échec: %s", db_exc)
        raise DeployError(message) from exc

    db.upsert_status(app_id, ref, "HEALTHY", "Déploiement validé par healthcheck")
    logger.info("=== Déploiement %s (%s) terminé avec succès ===", app_id, ref)
