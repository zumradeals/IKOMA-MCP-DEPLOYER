"""Interfaces de déploiement (stubs).

Aucune logique métier ni appel Docker n'est réalisé ici : uniquement les signatures
et contrats documentés pour l'implémentation future.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DeployContext:
    """Contexte minimal pour piloter un déploiement."""

    environment: str
    service: str
    release_id: Optional[str] = None
    dry_run: bool = False


def up(ctx: DeployContext) -> None:
    """Déclenche le déploiement d'une release sur un environnement donné.

    Args:
        ctx: Contexte décrivant l'environnement cible, le service, l'identifiant de release
            et un éventuel mode `dry_run` pour valider sans appliquer.

    Raises:
        NotImplementedError: toujours, tant que l'intégration Deployer n'est pas codée.
    """

    raise NotImplementedError("deploy.up sera implémenté avec le pilote IKOMA Deployer")


def rollback(ctx: DeployContext, reason: str | None = None) -> None:
    """Ordonne un rollback vers une release précédente.

    Args:
        ctx: Contexte identifiant l'environnement/le service et la release cible.
        reason: Optionnellement, la justification du rollback (audit/logs).

    Raises:
        NotImplementedError: toujours, tant que l'intégration Deployer n'est pas codée.
    """

    raise NotImplementedError("deploy.rollback sera implémenté avec le pilote IKOMA Deployer")
