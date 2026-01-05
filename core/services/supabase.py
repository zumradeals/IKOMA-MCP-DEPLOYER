"""Interface Supabase (stub)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass
class SupabaseConfig:
    """Configuration attendue pour initialiser/valider Supabase."""

    project_id: str
    api_key: str
    required_buckets: list[str]
    required_tables: list[str]
    options: Optional[Mapping[str, str]] = None


def ensure(config: SupabaseConfig) -> None:
    """Vérifie/initialise les ressources Supabase attendues.

    Args:
        config: Configuration déclarant les ressources (buckets, tables) et les secrets nécessaires.

    Raises:
        NotImplementedError: toujours, tant que l'intégration Supabase n'est pas codée.
    """

    raise NotImplementedError("ensure sera implémenté avec le client Supabase")
