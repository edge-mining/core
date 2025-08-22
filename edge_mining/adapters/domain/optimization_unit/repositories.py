"""Repositories for the Optimization Unit domain."""

import copy
import json
import sqlite3
from typing import Dict, List, Optional

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId
from edge_mining.domain.optimization_unit.aggregate_roots import EnergyOptimizationUnit
from edge_mining.domain.optimization_unit.exceptions import (
    OptimizationUnitAlreadyExistsError,
    OptimizationUnitConfigurationError,
    OptimizationUnitError,
    OptimizationUnitNotFoundError,
)
from edge_mining.domain.optimization_unit.ports import EnergyOptimizationUnitRepository


class InMemoryOptimizationUnitRepository(EnergyOptimizationUnitRepository):
    """In-Memory implementation for the Optimization Unit Repository."""

    def __init__(
        self,
        initial_units: Optional[Dict[EntityId, EnergyOptimizationUnit]] = None,
    ):
        self._optimization_units: Dict[EntityId, EnergyOptimizationUnit] = (
            copy.deepcopy(initial_units) if initial_units else {}
        )

    def add(self, optimization_unit: EnergyOptimizationUnit) -> None:
        """Add an optimization unit to the In-Memory repository."""
        if optimization_unit.id in self._optimization_units:
            # Handle update or raise error depending on desired behavior
            print(f"Warning: Optimization Unit {optimization_unit.id} already exists, overwriting.")
        self._optimization_units[optimization_unit.id] = copy.deepcopy(optimization_unit)

    def get_by_id(self, optimization_unit_id: EntityId) -> Optional[EnergyOptimizationUnit]:
        """Get an optimization unit by ID from the In-Memory repository."""
        return copy.deepcopy(self._optimization_units.get(optimization_unit_id))

    def get_all_enabled(self) -> List[EnergyOptimizationUnit]:
        """Get all enabled optimization units from the In-Memory repository."""
        return [copy.deepcopy(u) for u in self._optimization_units.values() if u.is_enabled]

    def get_all(self) -> List[EnergyOptimizationUnit]:
        """Get all optimization units from the In-Memory repository."""
        return [copy.deepcopy(u) for u in self._optimization_units.values()]

    def update(self, optimization_unit: EnergyOptimizationUnit) -> None:
        """Update an optimization unit in the In-Memory repository."""
        if optimization_unit.id not in self._optimization_units:
            raise ValueError(f"Optimization Unit {optimization_unit.id} not found for update.")
        self._optimization_units[optimization_unit.id] = copy.deepcopy(optimization_unit)

    def remove(self, optimization_unit_id: EntityId) -> None:
        """Remove an optimization unit from the In-Memory repository."""
        if optimization_unit_id in self._optimization_units:
            del self._optimization_units[optimization_unit_id]


class SqliteOptimizationUnitRepository(EnergyOptimizationUnitRepository):
    """SQLite implementation for the Optimization Unit Repository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables for the Optimization Unit domain if they do not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for Optimization Unit Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS optimization_units (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                is_enabled INTEGER NOT NULL DEFAULT 0 CHECK(is_enabled IN (0,1)),
                policy_id TEXT,
                target_miner_ids TEXT, -- JSON list of MinerId strings
                energy_source_id TEXT,
                home_forecast_provider_id TEXT,
                performance_tracker_id TEXT,
                notifier_ids TEXT -- JSON list of NotifierId strings
            );
            """
        ]

        conn = self._db.get_connection()

        try:
            with conn:
                cursor = conn.cursor()
                for statement in sql_statements:
                    cursor.execute(statement)

                self.logger.debug("Optimization Units tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise OptimizationUnitConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _row_to_optimization_unit(self, row: sqlite3.Row) -> Optional[EnergyOptimizationUnit]:
        """Deserialize a row from the database into a EnergyOptimizationUnit object."""
        if not row:
            return None
        try:
            # Deserialize JSON lists of target IDs
            target_ids_data = json.loads(row["target_miner_ids"] or "[]")
            notifier_ids_data = json.loads(row["notifier_ids"] or "[]")

            target_miner_ids = [EntityId(tid) for tid in target_ids_data]
            notifier_ids = [EntityId(nid) for nid in notifier_ids_data]

            return EnergyOptimizationUnit(
                id=EntityId(row["id"]),
                name=row["name"],
                description=row["description"],
                is_enabled=bool(row["is_enabled"]),
                policy_id=(EntityId(row["policy_id"]) if row["policy_id"] else None),
                target_miner_ids=target_miner_ids,
                energy_source_id=(EntityId(row["energy_source_id"]) if row["energy_source_id"] else None),
                home_forecast_provider_id=(
                    EntityId(row["home_forecast_provider_id"]) if row["home_forecast_provider_id"] else None
                ),
                performance_tracker_id=(
                    EntityId(row["performance_tracker_id"]) if row["performance_tracker_id"] else None
                ),
                notifier_ids=notifier_ids,
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing Optimization Unit from DB row: {row}. Error: {e}")
            return None

    def add(self, optimization_unit: EnergyOptimizationUnit) -> None:
        """Add an optimization unit to the SQLite database."""
        self.logger.debug(f"Adding optimization unit {optimization_unit.id} to SQLite.")
        sql = """
            INSERT INTO optimization_units (id, name, description, is_enabled, policy_id, target_miner_ids,
            energy_source_id, home_forecast_provider_id, performance_tracker_id, notifier_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._db.get_connection()
        try:
            # Serialize JSON lists of target IDs
            target_ids_json = json.dumps([str(tid) for tid in optimization_unit.target_miner_ids])
            notifier_ids_json = json.dumps([str(nid) for nid in optimization_unit.notifier_ids])

            with conn:
                conn.execute(
                    sql,
                    (
                        optimization_unit.id,
                        optimization_unit.name,
                        optimization_unit.description,
                        1 if optimization_unit.is_enabled else 0,
                        optimization_unit.policy_id,
                        target_ids_json,
                        optimization_unit.energy_source_id,
                        optimization_unit.home_forecast_provider_id,
                        optimization_unit.performance_tracker_id,
                        notifier_ids_json,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding optimization unit '{optimization_unit.name}': {e}")
            raise OptimizationUnitAlreadyExistsError(
                f"Optimization Unit with ID {optimization_unit.id} or name "
                f"'{optimization_unit.name}' already exists: {e}"
            ) from e
        except Exception as e:
            self.logger.error(f"Error adding optimization unit '{optimization_unit.name}': {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_by_id(self, optimization_unit_id: EntityId) -> Optional[EnergyOptimizationUnit]:
        """Get an optimization unit by ID from the SQLite database."""
        self.logger.debug(f"Getting optimization unit {optimization_unit_id} from SQLite.")
        sql = "SELECT * FROM optimization_units WHERE id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (optimization_unit_id,))
            row = cursor.fetchone()
            return self._row_to_optimization_unit(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting optimization unit {optimization_unit_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_all_enabled(self) -> List[EnergyOptimizationUnit]:
        """Get all enabled optimization units from the SQLite database."""
        self.logger.debug("Getting all enabled optimization units from SQLite.")
        sql = "SELECT * FROM optimization_units WHERE is_enabled = 1"
        conn = self._db.get_connection()
        optimization_units = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                optimization_unit = self._row_to_optimization_unit(row)
                if optimization_unit:
                    optimization_units.append(optimization_unit)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all enabled optimization units: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return optimization_units

    def get_all(self) -> List[EnergyOptimizationUnit]:
        """Get all optimization units from the SQLite database."""
        self.logger.debug("Getting all optimization units from SQLite.")
        sql = "SELECT * FROM optimization_units"
        conn = self._db.get_connection()
        optimization_units = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                optimization_unit = self._row_to_optimization_unit(row)
                if optimization_unit:
                    optimization_units.append(optimization_unit)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all enabled optimization units: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return optimization_units

    def update(self, optimization_unit: EnergyOptimizationUnit) -> None:
        """Update an optimization unit in the SQLite database."""
        self.logger.debug(f"Updating optimization unit {optimization_unit.id} in SQLite.")
        sql = """
            UPDATE optimization_units
            SET name = ?, description = ?, is_enabled = ?, policy_id = ?, target_miner_ids = ?, energy_source_id = ?,
            home_forecast_provider_id = ?, performance_tracker_id = ?, notifier_ids = ?
            WHERE id = ?
        """
        conn = self._db.get_connection()
        try:
            # Serialize JSON lists of target IDs
            target_ids_json = json.dumps([str(tid) for tid in optimization_unit.target_miner_ids])
            notifier_ids_json = json.dumps([str(nid) for nid in optimization_unit.notifier_ids])

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        optimization_unit.name,
                        optimization_unit.description,
                        1 if optimization_unit.is_enabled else 0,
                        optimization_unit.policy_id,
                        target_ids_json,
                        optimization_unit.energy_source_id,
                        optimization_unit.home_forecast_provider_id,
                        optimization_unit.performance_tracker_id,
                        notifier_ids_json,
                        optimization_unit.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise OptimizationUnitNotFoundError(
                        f"No optimization unit found with ID {optimization_unit.id} for update."
                    )
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating optimization unit {optimization_unit.id}: {e}")
            raise OptimizationUnitError(f"DB error updating optimization unit: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, optimization_unit_id: EntityId) -> None:
        """Remove an optimization unit from the SQLite database."""
        self.logger.debug(f"Removing optimization unit {optimization_unit_id} from SQLite.")
        sql = "DELETE FROM optimization_units WHERE id = ?"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (optimization_unit_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(
                        f"Attempt to remove non-existent optimization unit with ID {optimization_unit_id}."
                    )
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing optimization unit {optimization_unit_id}: {e}")
            raise OptimizationUnitError(f"DB error removing optimization unit: {e}") from e
        finally:
            if conn:
                conn.close()
