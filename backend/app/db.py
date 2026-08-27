from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "saizhi.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS uploads (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL, kind TEXT NOT NULL,
              filename TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL,
              validation_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL, status TEXT NOT NULL,
              current_step TEXT, storyline_json TEXT, quality_json TEXT,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS job_steps (
              id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
              step_key TEXT NOT NULL, label TEXT NOT NULL, status TEXT NOT NULL,
              output_json TEXT, error TEXT, started_at TEXT, finished_at TEXT,
              UNIQUE(job_id, step_key)
            );
            CREATE TABLE IF NOT EXISTS slides (
              id TEXT PRIMARY KEY, job_id TEXT NOT NULL, slide_number INTEGER NOT NULL,
              title TEXT, notes TEXT, elements_json TEXT NOT NULL,
              thumbnail_data TEXT
            );
            CREATE TABLE IF NOT EXISTS suggestions (
              id TEXT PRIMARY KEY, job_id TEXT NOT NULL, slide_number INTEGER NOT NULL,
              category TEXT NOT NULL, severity TEXT NOT NULL, title TEXT NOT NULL,
              description TEXT NOT NULL, action TEXT NOT NULL, rationale TEXT NOT NULL,
              automation TEXT NOT NULL, status TEXT NOT NULL, edited_action TEXT
            );
            CREATE TABLE IF NOT EXISTS revisions (
              id TEXT PRIMARY KEY, job_id TEXT NOT NULL, plan_json TEXT NOT NULL,
              status TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def load(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    return json.loads(value)
