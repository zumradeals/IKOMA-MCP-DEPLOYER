from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from core.deploy.deploy_up import DB_PATH


@dataclass
class AppConfig:
    app_id: str
    repo_git_url: str
    branch: str = "main"
    path_deploiement: str = ""
    migrations_dir: str = ""
    type_app: str = "generic"


class AppConfigStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_configs (
                    app_id TEXT PRIMARY KEY,
                    repo_git_url TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    path_deploiement TEXT NOT NULL,
                    migrations_dir TEXT,
                    type_app TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def list_configs(self) -> List[AppConfig]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT app_id, repo_git_url, branch, path_deploiement, migrations_dir, type_app FROM app_configs ORDER BY app_id"
            ).fetchall()
            return [AppConfig(**dict(row)) for row in rows]

    def get(self, app_id: str) -> Optional[AppConfig]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT app_id, repo_git_url, branch, path_deploiement, migrations_dir, type_app FROM app_configs WHERE app_id = ?",
                (app_id,),
            ).fetchone()
            if row:
                return AppConfig(**dict(row))
            return None

    def upsert(self, config: AppConfig) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO app_configs (app_id, repo_git_url, branch, path_deploiement, migrations_dir, type_app)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO UPDATE SET
                    repo_git_url=excluded.repo_git_url,
                    branch=excluded.branch,
                    path_deploiement=excluded.path_deploiement,
                    migrations_dir=excluded.migrations_dir,
                    type_app=excluded.type_app
                """,
                (
                    config.app_id,
                    config.repo_git_url,
                    config.branch,
                    config.path_deploiement,
                    config.migrations_dir,
                    config.type_app,
                ),
            )
            conn.commit()
