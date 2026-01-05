from __future__ import annotations

from pathlib import Path

from core.deploy.deploy_up import ReleaseConfig
from core.logging.logger import run_command


def compose_up(release: ReleaseConfig, repo_dir: Path, logger) -> None:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(release.compose_file),
        "up",
        "-d",
    ]
    if release.services:
        cmd.extend(release.services)

    logger.info("Exécution: %s", " ".join(cmd))
    run_command(cmd, cwd=repo_dir, logger=logger)
