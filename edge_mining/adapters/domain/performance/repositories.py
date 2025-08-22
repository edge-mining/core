"""Repositories for Performance Tracker Domain."""

import copy
import json
import sqlite3
from typing import Dict, List, Optional

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId
from edge_mining.domain.exceptions import ConfigurationError
from edge_mining.domain.performance.common import MiningPerformanceTrackerAdapter
from edge_mining.domain.performance.entities import MiningPerformanceTracker
from edge_mining.domain.performance.exceptions import (
    MiningPerformanceTrackerAlreadyExistsError,
    MiningPerformanceTrackerConfigurationError,
    MiningPerformanceTrackerNotFoundError,
)
from edge_mining.domain.performance.ports import MiningPerformanceTrackerRepository
from edge_mining.shared.adapter_maps.performance import (
    MINING_PERFORMANCE_TRACKER_CONFIG_TYPE_MAP,
)
from edge_mining.shared.interfaces.config import MiningPerformanceTrackerConfig


class InMemoryMiningPerformanceTrackerRepository(MiningPerformanceTrackerRepository):
    """In-Memory implementation of the MiningPerformanceTrackerRepository."""

    def __init__(
        self,
        initial_trackers: Optional[Dict[EntityId, MiningPerformanceTracker]] = None,
    ):
        self._trackers: Dict[EntityId, MiningPerformanceTracker] = (
            copy.deepcopy(initial_trackers) if initial_trackers else {}
        )

    def add(self, tracker: MiningPerformanceTracker) -> None:
        if tracker.id in self._trackers:
            raise MiningPerformanceTrackerAlreadyExistsError(
                f"Performance Tracker with ID {tracker.id} already exists."
            )
        self._trackers[tracker.id] = tracker

    def get_by_id(self, tracker_id: EntityId) -> Optional[MiningPerformanceTracker]:
        return copy.deepcopy(self._trackers.get(tracker_id))

    def get_all(self) -> List[MiningPerformanceTracker]:
        return [copy.deepcopy(t) for t in self._trackers.values()]

    def update(self, tracker: MiningPerformanceTracker) -> None:
        if tracker.id not in self._trackers:
            raise MiningPerformanceTrackerNotFoundError(f"Performance Tracker with ID {tracker.id} not found.")
        self._trackers[tracker.id] = copy.deepcopy(tracker)

    def remove(self, tracker_id: EntityId) -> None:
        if tracker_id in self._trackers:
            del self._trackers[tracker_id]

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[MiningPerformanceTracker]:
        return [copy.deepcopy(t) for t in self._trackers.values() if t.external_service_id == external_service_id]


class SqliteMiningPerformanceTrackerRepository(MiningPerformanceTrackerRepository):
    """SQLite implementation of the MiningPerformanceTrackerRepository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger
        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables for the Performance Tracker domain if they do not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for Performance Tracker Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS mining_performance_trackers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                adapter_type TEXT NOT NULL,
                config TEXT, -- JSON object of config
                external_service_id TEXT -- Optional ID for external service integration
            );
            """
        ]

        conn = self._db.get_connection()

        try:
            with conn:
                for sql in sql_statements:
                    conn.execute(sql)
                self.logger.debug("Mining Performance Tracker tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error creating tables: {e}")
            raise ConfigurationError(f"SQLite error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _deserialize_config(
        self, adapter_type: MiningPerformanceTrackerAdapter, config_json: str
    ) -> MiningPerformanceTrackerConfig:
        """Deserialize the JSON string into a MiningPerformanceTrackerConfig object."""
        data: dict = json.loads(config_json)

        if adapter_type not in MINING_PERFORMANCE_TRACKER_CONFIG_TYPE_MAP:
            raise MiningPerformanceTrackerConfigurationError(
                f"Error reading MiningPerformanceTracker configuration. Invalid type '{adapter_type}'"
            )

        config_class: Optional[type[MiningPerformanceTrackerConfig]] = MINING_PERFORMANCE_TRACKER_CONFIG_TYPE_MAP.get(
            adapter_type
        )
        if not config_class:
            raise MiningPerformanceTrackerConfigurationError(
                f"Error creating MiningPerformanceTracker configuration. Type '{adapter_type}'"
            )

        config_instance = config_class.from_dict(data)
        if not isinstance(config_instance, MiningPerformanceTrackerConfig):
            raise MiningPerformanceTrackerConfigurationError(
                f"Error creating MiningPerformanceTracker configuration. Type '{adapter_type}'"
            )
        return config_instance

    def _row_to_tracker(self, row: sqlite3.Row) -> Optional[MiningPerformanceTracker]:
        """Deserialize a row from the database into a MiningPerformanceTracker object."""
        if not row:
            return None
        try:
            adapter_type = MiningPerformanceTrackerAdapter(row["adapter_type"])

            # Deserialize config from the database row
            config = self._deserialize_config(adapter_type, row["config"])

            return MiningPerformanceTracker(
                id=EntityId(row["id"]),
                name=row["name"],
                adapter_type=adapter_type,
                config=config,
                external_service_id=(EntityId(row["external_service_id"]) if row["external_service_id"] else None),
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing MiningPerformanceTracker from DB row: {row}. Error: {e}")
            return None

    def add(self, tracker: MiningPerformanceTracker) -> None:
        """Add a new mining performance tracker to the repository."""
        self.logger.debug(f"Adding mining performance tracker {tracker.id} to SQLite repository.")
        sql = """
            INSERT INTO mining_performance_trackers (id, name, adapter_type, config, external_service_id)
            VALUES (?, ?, ?, ?, ?);
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if tracker.config:
                config_json = json.dumps(tracker.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        tracker.id,
                        tracker.name,
                        tracker.adapter_type.value,
                        config_json,
                        tracker.external_service_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding mining performance tracker {tracker.id}: {e}")
            # Could mean that the ID already exists
            raise MiningPerformanceTrackerAlreadyExistsError(
                f"Mining performance tracker with ID {tracker.id} already exists or constraint violation: {e}"
            ) from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding mining performance tracker {tracker.id}: {e}")
            raise MiningPerformanceTrackerConfigurationError(f"DB error adding mining performance tracker: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, tracker_id: EntityId) -> Optional[MiningPerformanceTracker]:
        """Retrieve a mining performance tracker by its ID."""
        self.logger.debug(f"Retrieving mining performance tracker {tracker_id} from SQLite repository.")
        sql = "SELECT * FROM mining_performance_trackers WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (tracker_id,))
            row = cursor.fetchone()
            return self._row_to_tracker(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving mining performance tracker {tracker_id}: {e}")
            raise MiningPerformanceTrackerNotFoundError(f"DB error retrieving mining performance tracker: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[MiningPerformanceTracker]:
        """Retrieve all mining performance trackers from the repository."""
        self.logger.debug("Retrieving all mining performance trackers from SQLite repository.")
        sql = "SELECT * FROM mining_performance_trackers;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            trackers = []
            for row in rows:
                tracker = self._row_to_tracker(row)
                if tracker:
                    trackers.append(tracker)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving all mining performance trackers: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return trackers

    def update(self, tracker: MiningPerformanceTracker) -> None:
        """Update an existing mining performance tracker in the repository."""
        self.logger.debug(f"Updating mining performance tracker {tracker.id} in SQLite repository.")
        sql = """
            UPDATE mining_performance_trackers
            SET name = ?, adapter_type = ?, config = ?, external_service_id = ?
            WHERE id = ?;
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if tracker.config:
                config_json = json.dumps(tracker.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        tracker.name,
                        tracker.adapter_type.value,
                        config_json,
                        tracker.external_service_id,
                        tracker.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise MiningPerformanceTrackerNotFoundError(
                        f"mining performance tracker with ID {tracker.id} not found."
                    )
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating mining performance tracker {tracker.id}: {e}")
            raise MiningPerformanceTrackerConfigurationError(
                f"DB error updating mining performance tracker: {e}"
            ) from e
        finally:
            if conn:
                conn.close()

    def remove(self, tracker_id: EntityId) -> None:
        """Remove a mining performance tracker from the repository."""
        self.logger.debug(f"Removing mining performance tracker {tracker_id} from SQLite repository.")
        sql = "DELETE FROM mining_performance_trackers WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (tracker_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(f"Attempted to remove non-existent mining performance tracker {tracker_id}.")
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing mining performance tracker {tracker_id}: {e}")
            raise MiningPerformanceTrackerConfigurationError(
                f"DB error removing mining performance tracker: {e}"
            ) from e
        finally:
            if conn:
                conn.close()

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[MiningPerformanceTracker]:
        """Get all mining performance trackers associated with a specific external service ID."""
        self.logger.debug(
            f"Retrieving mining performance trackers for external service {external_service_id} from SQLite repository."
        )
        sql = "SELECT * FROM mining_performance_trackers WHERE external_service_id = ?;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (external_service_id,))
            rows = cursor.fetchall()
            trackers = []
            for row in rows:
                tracker = self._row_to_tracker(row)
                if tracker:
                    trackers.append(tracker)
            return trackers
        except sqlite3.Error as e:
            self.logger.error(
                f"SQLite error retrieving mining performance trackers for external service {external_service_id}: {e}"
            )
            return []
        finally:
            if conn:
                conn.close()
