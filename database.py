import os
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS student (
    ID_S   INTEGER PRIMARY KEY AUTOINCREMENT,
    FN     TEXT NOT NULL,
    LN     TEXT NOT NULL,
    Major  TEXT NOT NULL CHECK (Major IN
           ('Finance', 'Business Analytics', 'Information Technology',
            'Marketing', 'Accounting')),
    dmajor INTEGER NOT NULL DEFAULT 0 CHECK (dmajor IN (0, 1)),
    level  TEXT NOT NULL CHECK (level IN
           ('Freshman', 'Sophomore', 'Junior', 'Senior'))
);

CREATE TABLE IF NOT EXISTS report (
    ID_R        INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_S        INTEGER NOT NULL,
    Title       TEXT NOT NULL,
    Type        TEXT NOT NULL,
    k1          TEXT,
    k2          TEXT,
    k3          TEXT,
    releaseDate TEXT,
    FOREIGN KEY (ID_S) REFERENCES student (ID_S) ON DELETE CASCADE
);
"""


class Database:
    """Object that owns the connection to the SQLite file."""

    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        is_new = not os.path.exists(path)      # file is created on first connect
        with self.transaction() as conn:
            conn.executescript(SCHEMA)         # creates the 2 tables if missing
            if is_new:
                self._seed(conn)

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row         # rows behave like dictionaries
        conn.execute("PRAGMA foreign_keys = ON")   # enforce the student link
        return conn

    @contextmanager
    def transaction(self):
        """Open a connection; commit if all went well, roll back on error."""
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, sql, params=(), one=False):
        """SELECT. Returns a list of rows, or a single row/None if one=True."""
        conn = self.connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        if one:
            return rows[0] if rows else None
        return rows

    def execute(self, sql, params=()):
        """INSERT / UPDATE / DELETE. Returns (new_row_id, rows_changed)."""
        with self.transaction() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid, cur.rowcount

    def status(self):
        """Proof of connection: file name, tables and how many rows each has."""
        names = [r["name"] for r in self.query(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
        counts = {n: self.query(f"SELECT COUNT(*) AS c FROM {n}", one=True)["c"]
                  for n in names}
        return {"connected": True,
                "database_file": os.path.basename(self.path),
                "tables": counts}

    @staticmethod
    def _seed(conn):
        """First-run data: your original student and report."""
        conn.execute(
            "INSERT INTO student (FN, LN, Major, dmajor, level) "
            "VALUES ('Haythem', 'Ftirich', 'Information Technology', 0, 'Senior')")
        conn.execute(
            "INSERT INTO report (ID_S, Title, Type, k1, k2, k3, releaseDate) "
            "VALUES (1, 'Web Services', 'Technical', 'Flask', 'REST API', "
            "'Python', '2026-03-20')")