"""
This module contains the BaseSqliteRepository class, which is the base class for all SQLite repositories.
It provides a base implementation for creating tables and getting connections to the SQLite database.
"""

import sqlite3
import uuid

from edge_mining.shared.logging.port import LoggerPort

# Register an adapter and a converter
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
# sqlite3.register_converter("UUID", lambda u: uuid.UUID(u.decode("utf-8")))


class BaseSqliteRepository:
    """Base class for SQLite repositories."""

    def __init__(self, db_path: str, logger: LoggerPort):
        self.db_path = db_path
        self.logger = logger

    def get_connection(self):
        """Obtain a database connection."""
        try:
            # We set a timeout for blocking operations
            conn = sqlite3.connect(self.db_path, timeout=10, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.row_factory = sqlite3.Row  # Accessing columns by name
            conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign keys if used

            return conn
        except sqlite3.Error as e:
            self.logger.error(f"SQLite DB connection error ({self.db_path}): {e}")
            raise ConnectionError(f"SQLite Connection Error: {e}") from e
