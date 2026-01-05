from __future__ import annotations

import os
from pathlib import Path

from core.deploy.deploy_up import DeployError
from core.logging.logger import run_command


def sync_repository(app_id: str, ref: str, repos_dir: Path, logger) -> Path:
    """Clone ou met à jour le dépôt applicatif."""

    repos_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = repos_dir / app_id
    remote_url = os.getenv("IKOMA_GIT_REMOTE")

    if repo_dir.exists():
        logger.info("Repo %s déjà présent, fetch + checkout", repo_dir)
        run_command(["git", "fetch", "--all", "--prune"], cwd=repo_dir, logger=logger)
        run_command(["git", "checkout", ref], cwd=repo_dir, logger=logger)
        run_command(["git", "pull", "--ff-only"], cwd=repo_dir, logger=logger)
    else:
        if not remote_url:
            raise DeployError(
                "Impossible de cloner : définir la variable d'environnement IKOMA_GIT_REMOTE",
            )
        logger.info("Clonage de %s dans %s", remote_url, repo_dir)
        run_command(["git", "clone", remote_url, str(repo_dir)], logger=logger)
        run_command(["git", "checkout", ref], cwd=repo_dir, logger=logger)

    return repo_dir
