from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    public_user_id TEXT,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    email_verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    lockout_level INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    last_failed_login_at TEXT,
    last_login_at TEXT,
    last_otp_verified_at TEXT
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT,
    organization TEXT,
    monitoring_focus TEXT,
    primary_os TEXT,
    host_environment TEXT,
    log_source_preference TEXT,
    live_trace_os_preference TEXT,
    avatar_path TEXT,
    preferred_theme TEXT NOT NULL DEFAULT 'campus',
    preferred_analysis_mode TEXT NOT NULL DEFAULT 'compare',
    notification_preference TEXT NOT NULL DEFAULT 'important-only',
    greeting_style TEXT NOT NULL DEFAULT 'warm',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    run_key TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    filename TEXT NOT NULL,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS human_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    challenge_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    answer_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trusted_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    device_label TEXT,
    user_agent TEXT,
    expires_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    feedback_key TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    overall_rating INTEGER NOT NULL,
    usability_rating INTEGER NOT NULL,
    visual_rating INTEGER NOT NULL,
    clarity_rating INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    question TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_runs_user_created ON user_runs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_uploads_user_created ON user_uploads(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_human_challenges_user_type ON human_challenges(user_id, challenge_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_user_created ON trusted_devices(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_records_user_created ON feedback_records(user_id, created_at DESC);
"""


def get_db_path(base_dir: Path) -> Path:
    runtime_dir = base_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / "workbench.db"


def connect_db(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    _ensure_column(connection, "users", "public_user_id", "TEXT")
    _ensure_column(connection, "users", "failed_login_attempts", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "users", "lockout_level", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "users", "locked_until", "TEXT")
    _ensure_column(connection, "users", "last_failed_login_at", "TEXT")
    _ensure_column(connection, "user_profiles", "first_name", "TEXT")
    _ensure_column(connection, "user_profiles", "last_name", "TEXT")
    _ensure_column(connection, "user_profiles", "primary_os", "TEXT")
    _ensure_column(connection, "user_profiles", "host_environment", "TEXT")
    _ensure_column(connection, "user_profiles", "log_source_preference", "TEXT")
    _ensure_column(connection, "user_profiles", "live_trace_os_preference", "TEXT")
    _ensure_column(connection, "user_profiles", "avatar_path", "TEXT")
    connection.commit()


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def load_json(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
