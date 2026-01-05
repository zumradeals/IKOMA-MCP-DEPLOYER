from __future__ import annotations

import logging
from pathlib import Path
from typing import List


def build_logger(app_id: str, logs_dir: Path, log_filename: str = "deploy.log") -> logging.Logger:
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_log_dir = logs_dir / app_id
    app_log_dir.mkdir(parents=True, exist_ok=True)
    log_file = app_log_dir / log_filename

    logger = logging.getLogger(f"{log_filename}.{app_id}")
    logger.setLevel(logging.INFO)

    if not any(isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_file) for handler in logger.handlers):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


def run_command(command: List[str], logger: logging.Logger, cwd: Path | None = None) -> None:
    logger.info("$ %s", " ".join(command))
    from subprocess import PIPE, STDOUT, run

    result = run(command, cwd=cwd, stdout=PIPE, stderr=STDOUT, text=True, check=False)
    if result.stdout:
        logger.info(result.stdout.strip())

    if result.returncode != 0:
        error_msg = f"Commande échouée ({result.returncode}): {' '.join(command)}"
        logger.error(error_msg)
        from core.deploy.deploy_up import DeployError

        raise DeployError(error_msg)
