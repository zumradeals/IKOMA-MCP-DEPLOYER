"""Interface de restauration (stub)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .backup import BackupTarget


@dataclass
class RestoreRequest:
    """Paramètres nécessaires à une restauration."""

    target: BackupTarget
    snapshot_id: str
    validate_only: bool = False
    notes: Optional[str] = None


def run(request: RestoreRequest) -> None:
    """Restaure un backup spécifié pour un service/environnement.

    Args:
        request: Inclut l'identifiant de snapshot à restaurer et la cible applicative.

    Raises:
        NotImplementedError: toujours, tant que l'intégration de restauration n'est pas codée.
    """

    raise NotImplementedError("restore.run sera implémenté avec le backend de restauration choisi")
