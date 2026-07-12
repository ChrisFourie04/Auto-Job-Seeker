import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta


class DatabaseManager:
    """Manages SQLite database for tracking seen job listings."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create the seen_jobs table if it doesn't exist."""
        try:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    title TEXT,
                    company TEXT,
                    url TEXT,
                    relevance_score REAL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notified BOOLEAN DEFAULT 0,
                    UNIQUE(source, external_id)
                );
            """)
            conn.commit()
            conn.close()
            self.logger.info("Database initialized at %s", self.db_path)
        except sqlite3.Error as e:
            self.logger.error("Failed to initialize database: %s", e)
            raise

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new database connection with Row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def is_seen(self, source: str, external_id: str) -> bool:
        """Check if a job has already been seen by source and external_id."""
        try:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT 1 FROM seen_jobs WHERE source = ? AND external_id = ?",
                (source, external_id),
            )
            result = cursor.fetchone() is not None
            conn.close()
            return result
        except sqlite3.Error as e:
            self.logger.error("Error checking seen status: %s", e)
            return False

    def mark_seen(
        self,
        source: str,
        external_id: str,
        title: str,
        company: str,
        url: str,
        score: float,
        notified: bool = False,
    ) -> None:
        """Mark a job as seen. Uses INSERT OR IGNORE for deduplication."""
        try:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT OR IGNORE INTO seen_jobs
                    (source, external_id, title, company, url, relevance_score, notified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (source, external_id, title, company, url, score, notified),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            self.logger.error("Error marking job as seen: %s", e)

    def get_stats(self) -> dict:
        """Return statistics about the seen_jobs table."""
        try:
            conn = self._get_conn()

            total = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]

            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            today = conn.execute(
                "SELECT COUNT(*) FROM seen_jobs WHERE first_seen >= ?",
                (today_start,),
            ).fetchone()[0]

            notified = conn.execute(
                "SELECT COUNT(*) FROM seen_jobs WHERE notified = 1"
            ).fetchone()[0]

            source_rows = conn.execute(
                "SELECT source, COUNT(*) as count FROM seen_jobs GROUP BY source"
            ).fetchall()
            sources = {row["source"]: row["count"] for row in source_rows}

            conn.close()
            return {
                "total": total,
                "today": today,
                "notified": notified,
                "sources": sources,
            }
        except sqlite3.Error as e:
            self.logger.error("Error getting stats: %s", e)
            return {"total": 0, "today": 0, "notified": 0, "sources": {}}

    def cleanup(self, days: int = 30) -> int:
        """Delete jobs older than the specified number of days. Returns count deleted."""
        try:
            conn = self._get_conn()
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor = conn.execute(
                "DELETE FROM seen_jobs WHERE first_seen < ?", (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            self.logger.info("Cleaned up %d jobs older than %d days", deleted, days)
            return deleted
        except sqlite3.Error as e:
            self.logger.error("Error during cleanup: %s", e)
            return 0
