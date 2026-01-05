from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


class DeploymentState:
    """Petit helper pour stocker l'état dans SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deployments (
                    app_id TEXT PRIMARY KEY,
                    ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS supabase_runs (
                    app_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message TEXT,
                    migrations TEXT NOT NULL
                )
                """
            )

    def upsert_status(self, app_id: str, ref: str, status: str, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO deployments(app_id, ref, status, updated_at, message)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO UPDATE SET
                    ref=excluded.ref,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    message=excluded.message
                """,
                (app_id, ref, status, timestamp, message),
            )

    def record_supabase_result(
        self, app_id: str, status: str, message: str, migrations: list[str]
    ) -> None:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = json.dumps(migrations, ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO supabase_runs(app_id, status, updated_at, message, migrations)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO UPDATE SET
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    message=excluded.message,
                    migrations=excluded.migrations
                """,
                (app_id, status, timestamp, message, payload),
            )
