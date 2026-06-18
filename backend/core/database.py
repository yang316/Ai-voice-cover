"""SQLite database for task persistence."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings

DB_PATH = settings.data_dir / "data" / "tasks.db"


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            step TEXT DEFAULT 'separating',
            progress INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            input_file TEXT,
            output_file TEXT,
            voice_id TEXT,
            backend TEXT,
            created_at TEXT,
            completed_at TEXT,
            error TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
    """)
    conn.commit()

    # Migrate: add 'step' column if missing (existing DBs)
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN step TEXT DEFAULT 'separating'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.close()


def save_task(task_id: str, **kwargs):
    """Save or update task in database."""
    conn = get_db()
    kwargs["task_id"] = task_id

    # Check if task exists
    existing = conn.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,)).fetchone()

    if existing:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs if k != "task_id")
        values = [v for k, v in kwargs.items() if k != "task_id"]
        values.append(task_id)
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE task_id = ?", values)
    else:
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        conn.execute(f"INSERT INTO tasks ({cols}) VALUES ({placeholders})", list(kwargs.values()))

    conn.commit()
    conn.close()


def get_task(task_id: str) -> dict | None:
    """Get task from database."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_tasks(limit: int = 50) -> list[dict]:
    """Get all tasks, newest first."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
