"""Primitives de déploiement IKOMA BRIDGE.

Ce package rassemble les fonctions concrètes pour piloter un déploiement
Docker Compose à partir d'un référentiel applicatif.
"""

from .deploy_up import deploy_up

__all__ = ["deploy_up"]
