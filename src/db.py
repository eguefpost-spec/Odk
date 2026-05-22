import sqlite3
from datetime import datetime
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            company     TEXT NOT NULL,
            location    TEXT,
            url         TEXT NOT NULL,
            easy_apply  INTEGER DEFAULT 0,
            description TEXT,
            discovered_at TEXT NOT NULL,
            status      TEXT DEFAULT 'new',
            applied_at  TEXT,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ran_at      TEXT NOT NULL,
            jobs_found  INTEGER DEFAULT 0,
            jobs_applied INTEGER DEFAULT 0
        );
    """)
    conn.commit()


def upsert_job(conn: sqlite3.Connection, job: dict) -> bool:
    """Returns True if the job is new."""
    existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job["id"],)).fetchone()
    if existing:
        return False
    conn.execute(
        """INSERT INTO jobs (id, title, company, location, url, easy_apply, description, discovered_at)
           VALUES (:id, :title, :company, :location, :url, :easy_apply, :description, :discovered_at)""",
        {**job, "discovered_at": datetime.now().isoformat()},
    )
    conn.commit()
    return True


def update_status(conn: sqlite3.Connection, job_id: str, status: str, notes: str = ""):
    applied_at = datetime.now().isoformat() if status == "applied" else None
    conn.execute(
        "UPDATE jobs SET status = ?, applied_at = ?, notes = ? WHERE id = ?",
        (status, applied_at, notes, job_id),
    )
    conn.commit()


def get_jobs(conn: sqlite3.Connection, status: str = None) -> list:
    if status:
        rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY discovered_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs ORDER BY discovered_at DESC").fetchall()
    return [dict(r) for r in rows]


def log_run(conn: sqlite3.Connection, jobs_found: int, jobs_applied: int):
    conn.execute(
        "INSERT INTO runs (ran_at, jobs_found, jobs_applied) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), jobs_found, jobs_applied),
    )
    conn.commit()
