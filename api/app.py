"""Entrée principale pour l'API IKOMA BRIDGE.

Ce module accueillera ultérieurement un framework (FastAPI/Flask/Express via API Gateway) ;
il liste dès à présent les endpoints attendus pour cadrer l'implémentation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ApiEndpoint:
    """Représente un endpoint attendu par l'API du Bridge."""

    method: str
    path: str
    description: str


EXPECTED_ENDPOINTS: List[ApiEndpoint] = [
    ApiEndpoint("GET", "/health", "Vérifier l'état du service API."),
    ApiEndpoint("POST", "/deployments", "Déclencher un déploiement vers un environnement."),
    ApiEndpoint(
        "POST",
        "/deployments/{id}/rollback",
        "Ordonner un rollback vers une release précédente pour un déploiement donné.",
    ),
    ApiEndpoint("GET", "/deployments/{id}", "Consulter l'état et les journaux d'un déploiement."),
    ApiEndpoint("POST", "/pipelines/run", "Démarrer un pipeline Lovable → GitHub → VPS."),
    ApiEndpoint("POST", "/supabase/ensure", "Vérifier et initialiser les ressources Supabase nécessaires."),
    ApiEndpoint("POST", "/backup/run", "Lancer un backup applicatif/infra."),
    ApiEndpoint("POST", "/restore/run", "Restaurer un backup spécifié."),
]


def create_app() -> None:
    """Prépare et renvoie l'application serveur.

    Cette fonction contiendra la configuration du framework (routes, middlewares, auth) et
    branchera les handlers Core. Elle reste vide tant que la pile technique n'est pas choisie.
    """

    # Exemple futur : app = FastAPI(...); déclarer routes et dépendances ici.
    # return app
    return None


if __name__ == "__main__":
    # Démarrage manuel (placeholder). À remplacer par un serveur réel (uvicorn/express).
    create_app()
    print("API IKOMA BRIDGE : serveur non implémenté (stub).")
