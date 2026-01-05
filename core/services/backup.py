"""Interface de sauvegarde (stub)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BackupTarget:
    """Décrit ce qui doit être sauvegardé."""

    service: str
    environment: str
    storage_uri: Optional[str] = None


def run(target: BackupTarget) -> None:
    """Lance un backup applicatif/infra pour le service donné.

    Args:
        target: Définition du périmètre de sauvegarde (service, environnement, stockage cible).

    Raises:
        NotImplementedError: toujours, tant que l'intégration backup n'est pas codée.
    """

    raise NotImplementedError("backup.run sera implémenté avec le backend de sauvegarde choisi")
