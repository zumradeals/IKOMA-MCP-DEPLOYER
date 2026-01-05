"""Gestion minimale des migrations Supabase (Postgres self-host)."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2 import sql

from core.logging.logger import build_logger
from core.store.sqlite_store import DeploymentState

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "ikoma.db"


@dataclass
class SupabaseConfig:
    """Configuration attendue pour initialiser/valider Supabase."""

    project_id: str
    api_key: str
    required_buckets: list[str]
    required_tables: list[str]
    options: Optional[Mapping[str, str]] = None


def ensure(config: SupabaseConfig) -> None:  # pragma: no cover - conservé pour compatibilité
    """Vérifie/initialise les ressources Supabase attendues."""

    raise NotImplementedError("ensure sera implémenté avec le client Supabase")


def supabase_connect(env: Mapping[str, str] | None = None) -> PgConnection:
    """Ouvre une connexion Postgres pour Supabase via DSN ou variables PG*.

    Args:
        env: mapping des variables d'environnement (par défaut os.environ).

    Returns:
        Connexion psycopg2 ouverte.

    Raises:
        ValueError: si aucune information de connexion n'est fournie.
    """

    env = env or os.environ
    dsn = env.get("SUPABASE_DB_DSN")
    if dsn:
        return psycopg2.connect(dsn)

    host = env.get("PGHOST")
    database = env.get("PGDATABASE")
    user = env.get("PGUSER")
    password = env.get("PGPASSWORD")
    port = env.get("PGPORT", "5432")

    if not (host and database and user):
        raise ValueError(
            "Aucun DSN Supabase fourni (SUPABASE_DB_DSN) et variables PG* incomplètes"
        )

    return psycopg2.connect(
        host=host,
        dbname=database,
        user=user,
        password=password,
        port=port,
    )


def _ensure_tracking_table(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ikoma_migrations (
                id SERIAL PRIMARY KEY,
                app_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(app_id, filename)
            )
            """
        )

        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'ikoma_migrations'
            """
        )
        columns = {row[0] for row in cur.fetchall()}

        if "name" in columns and "filename" not in columns:
            cur.execute("ALTER TABLE ikoma_migrations RENAME COLUMN name TO filename")
            columns.discard("name")
            columns.add("filename")

        if "checksum" not in columns:
            cur.execute("ALTER TABLE ikoma_migrations ADD COLUMN checksum TEXT")

        cur.execute("UPDATE ikoma_migrations SET checksum = '' WHERE checksum IS NULL")
        cur.execute("ALTER TABLE ikoma_migrations ALTER COLUMN checksum SET NOT NULL")
        cur.execute(
            "ALTER TABLE ikoma_migrations DROP CONSTRAINT IF EXISTS ikoma_migrations_app_id_name_key"
        )
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_name = 'ikoma_migrations'
                      AND tc.constraint_name = 'ikoma_migrations_app_id_filename_key'
                ) THEN
                    ALTER TABLE ikoma_migrations
                    ADD CONSTRAINT ikoma_migrations_app_id_filename_key UNIQUE(app_id, filename);
                END IF;
            END;
            $$;
            """
        )

        conn.commit()


def _get_existing_checksum(conn: PgConnection, app_id: str, filename: str) -> tuple[bool, str | None]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT checksum
            FROM ikoma_migrations
            WHERE app_id=%s AND filename=%s
            LIMIT 1
            """,
            (app_id, filename),
        )
        row = cur.fetchone()
        if not row:
            return False, None
        return True, row[0]


def _apply_file(conn: PgConnection, app_id: str, path: Path, checksum: str) -> None:
    sql_content = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        try:
            cur.execute(sql_content)
            cur.execute(
                """
                INSERT INTO ikoma_migrations(app_id, filename, checksum)
                VALUES(%s, %s, %s)
                """,
                (app_id, path.name, checksum),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def supabase_apply_migrations(
    app_id: str, repo_path: str | Path, migrations_dir: str = "supabase/migrations"
) -> list[str]:
    """Applique les migrations SQL Supabase d'un repo sur une instance Postgres.

    Les fichiers .sql sont appliqués dans l'ordre lexicographique et marqués dans
    la table ikoma_migrations pour éviter toute ré-application.
    """

    logger = build_logger(app_id, LOGS_DIR, log_filename="supabase.log")
    logger.info("=== Migration Supabase pour %s démarrée ===", app_id)

    repo_root = Path(repo_path)
    migrations_path = repo_root / migrations_dir
    if not migrations_path.is_dir():
        raise FileNotFoundError(f"Dossier de migrations introuvable: {migrations_path}")

    db_state = DeploymentState(DB_PATH)
    db_state.ensure_schema()

    applied: list[str] = []
    conn: PgConnection | None = None
    try:
        conn = supabase_connect()
        logger.info(
            "Connexion Supabase: host=%s port=%s db=%s user=%s",
            conn.info.host,
            conn.info.port,
            conn.info.dbname,
            conn.info.user,
        )

        schema = (os.environ.get("SUPABASE_DB_SCHEMA") or "public").strip() or "public"
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        logger.info("search_path fixé à %s", schema)

        _ensure_tracking_table(conn)

        for sql_file in sorted(p for p in migrations_path.glob("*.sql") if p.is_file()):
            checksum = hashlib.sha256(sql_file.read_bytes()).hexdigest()
            exists, existing_checksum = _get_existing_checksum(conn, app_id, sql_file.name)
            if exists:
                if existing_checksum and existing_checksum != checksum:
                    error_message = (
                        "Migration déjà appliquée avec un checksum différent: %s"
                        % sql_file.name
                    )
                    raise ValueError(error_message)
                logger.info("Migration déjà appliquée, skip: %s", sql_file.name)
                continue

            logger.info("Application de %s", sql_file.name)
            _apply_file(conn, app_id, sql_file, checksum)
            applied.append(sql_file.name)

        message = f"{len(applied)} migration(s) appliquée(s)"
        db_state.record_supabase_result(app_id, "COMPLETED", message, applied)
        logger.info("=== Migration Supabase terminée (%s) ===", message)
        return applied
    except Exception as exc:  # noqa: BLE001 - capture volontaire
        message = f"supabase_apply_migrations échoué: {exc}"
        logger.exception(message)
        try:
            db_state.record_supabase_result(app_id, "FAILED", message, applied)
        except Exception as db_exc:  # noqa: BLE001 - trace secondaire
            logger.exception("Impossible d'écrire le statut d'échec: %s", db_exc)
        raise
    finally:
        if conn is not None:
            conn.close()
