"""Repositories for the Energy domain."""

import copy
import json
import sqlite3
from typing import Any, Dict, List, Optional

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId, WattHours, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter, EnergySourceType
from edge_mining.domain.energy.entities import EnergyMonitor, EnergySource
from edge_mining.domain.energy.exceptions import (
    EnergyMonitorConfigurationError,
    EnergyMonitorError,
    EnergySourceAlreadyExistsError,
    EnergySourceConfigurationError,
    EnergySourceError,
    EnergySourceNotFoundError,
)
from edge_mining.domain.energy.ports import EnergyMonitorRepository, EnergySourceRepository
from edge_mining.domain.energy.value_objects import Battery, Grid
from edge_mining.shared.adapter_maps.energy import ENERGY_MONITOR_CONFIG_TYPE_MAP
from edge_mining.shared.interfaces.config import EnergyMonitorConfig


class InMemoryEnergySourceRepository(EnergySourceRepository):
    """In-Memory implementation for the Energy Source Repository."""

    def __init__(
        self,
        initial_energy_sources: Optional[Dict[EntityId, EnergySource]] = None,
    ):
        self._energy_sources: Dict[EntityId, EnergySource] = (
            copy.deepcopy(initial_energy_sources) if initial_energy_sources else {}
        )

    def add(self, energy_source: EnergySource) -> None:
        """Add an energy source to the In-Memory repository."""
        if energy_source.id in self._energy_sources:
            # Handle update or raise error depending on desired behavior
            print(f"Warning: Energy Source {energy_source.id} already exists, overwriting.")
        self._energy_sources[energy_source.id] = copy.deepcopy(energy_source)

    def get_by_id(self, energy_source_id: EntityId) -> Optional[EnergySource]:
        """Get an energy source by ID from the In-Memory repository."""
        return copy.deepcopy(self._energy_sources.get(energy_source_id))

    def get_all(self) -> List[EnergySource]:
        """Get all energy sources from the In-Memory repository."""
        return [copy.deepcopy(e) for e in self._energy_sources.values()]

    def update(self, energy_source: EnergySource) -> None:
        """Update an energy source in the In-Memory repository."""
        if energy_source.id not in self._energy_sources:
            raise EnergySourceError(f"Energy Source {energy_source.id} not found for update.")
        self._energy_sources[energy_source.id] = copy.deepcopy(energy_source)

    def remove(self, energy_source_id: EntityId) -> None:
        """Remove an energy source from the In-Memory repository."""
        if energy_source_id in self._energy_sources:
            del self._energy_sources[energy_source_id]


class SqliteEnergySourceRepository(EnergySourceRepository):
    """SQLite implementation for the Energy Source Repository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the tables for the Energy Source Repository."""
        self.logger.debug(f"Ensuring SQLite tables exist for Energy Source Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS energy_sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                nominal_power_max REAL,
                storage TEXT, -- JSON object of Battery
                grid TEXT, -- JSON object of Grid
                external_source REAL,
                energy_monitor_id TEXT,
                forecast_provider_id TEXT
            );
            """
        ]
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                for statement in sql_statements:
                    cursor.execute(statement)
                self.logger.debug("Energy Sources tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise EnergySourceConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _dict_to_battery(self, data: Dict[str, Any]) -> Battery:
        """Deserialize a dictionary (from JSON) into an Battery object."""
        return Battery(nominal_capacity=WattHours(data["nominal_capacity"]))

    def _dict_to_grid(self, data: Dict[str, Any]) -> Grid:
        """Deserialize a dictionary (from JSON) into an Grid object."""
        return Grid(contracted_power=Watts(data["contracted_power"]))

    def _row_to_energy_source(self, row: sqlite3.Row) -> Optional[EnergySource]:
        """Convert a SQLite row to an EnergySource object."""
        if not row:
            return None
        try:
            energy_source_type = EnergySourceType(row["type"])

            # Deserialize the storage and grid from the database row
            storage = self._dict_to_battery(json.loads(row["storage"])) if row["storage"] else None
            grid = self._dict_to_grid(json.loads(row["grid"])) if row["grid"] else None

            return EnergySource(
                id=EntityId(row["id"]),
                name=row["name"],
                type=energy_source_type,
                nominal_power_max=(Watts(row["nominal_power_max"]) if row["nominal_power_max"] else None),
                storage=storage,
                grid=grid,
                external_source=(Watts(row["external_source"]) if row["external_source"] else None),
                energy_monitor_id=(EntityId(row["energy_monitor_id"]) if row["energy_monitor_id"] else None),
                forecast_provider_id=(EntityId(row["forecast_provider_id"]) if row["forecast_provider_id"] else None),
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing EnergySource from DB row: {row}. Error: {e}")
            return None

    def add(self, energy_source: EnergySource) -> None:
        """Add an energy source to the SQLite database."""
        self.logger.debug(f"Adding energy source {energy_source.id} to SQLite.")

        sql = """
            INSERT INTO energy_sources (id, name, type, nominal_power_max, storage, grid, external_source,
            energy_monitor_id, forecast_provider_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._db.get_connection()
        try:
            # Serialize the storage and grid to JSON for storage
            storage_json = json.dumps(energy_source.storage.__dict__) if energy_source.storage else None
            grid_json = json.dumps(energy_source.grid.__dict__) if energy_source.grid else None

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        energy_source.id,
                        energy_source.name,
                        energy_source.type.value,
                        energy_source.nominal_power_max,
                        storage_json,
                        grid_json,
                        energy_source.external_source,
                        energy_source.energy_monitor_id,
                        energy_source.forecast_provider_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding energy source {energy_source.id}: {e}")
            # Could mean that the ID already exists
            raise EnergySourceAlreadyExistsError(
                f"Energy Source with ID {energy_source.id} already exists or constraint violation: {e}"
            ) from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding energy source {energy_source.id}: {e}")
            raise EnergySourceError(f"DB error adding energy source: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, energy_source_id: EntityId) -> Optional[EnergySource]:
        """Get an energy source by ID from the SQLite database."""
        self.logger.debug(f"Getting energy source {energy_source_id} from SQLite.")

        sql = "SELECT * FROM energy_sources WHERE id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (energy_source_id,))
            row = cursor.fetchone()
            return self._row_to_energy_source(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting energy source {energy_source_id}: {e}")
            return None  # Or raise exception? Returning None is more forgiving
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[EnergySource]:
        """Get all energy sources from the SQLite database."""
        self.logger.debug("Getting all energy sources from SQLite.")

        sql = "SELECT * FROM energy_sources"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            energy_sources = []
            for row in rows:
                energy_source = self._row_to_energy_source(row)
                if energy_source:
                    energy_sources.append(energy_source)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all energy sources: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return energy_sources

    def update(self, energy_source: EnergySource) -> None:
        """Update an energy source in the SQLite database."""
        self.logger.debug(f"Updating energy source {energy_source.id} in SQLite.")

        sql = """
            UPDATE energy_sources
            SET name = ?, type = ?, nominal_power_max = ?, storage = ?, grid = ?, external_source = ?,
            energy_monitor_id = ?, forecast_provider_id = ?
            WHERE id = ?
        """
        conn = self._db.get_connection()
        try:
            # Serialize the storage and grid to JSON for storage
            storage_json = json.dumps(energy_source.storage.__dict__) if energy_source.storage else None
            grid_json = json.dumps(energy_source.grid.__dict__) if energy_source.grid else None

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        energy_source.name,
                        energy_source.type.value,
                        energy_source.nominal_power_max,
                        storage_json,
                        grid_json,
                        energy_source.external_source,
                        energy_source.energy_monitor_id,
                        energy_source.forecast_provider_id,
                        energy_source.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise EnergySourceNotFoundError(f"No energy source found with ID {energy_source.id} for update.")
        except sqlite3.Error as e:
            self.logger.error(f"Error updating energy source {energy_source.id} in SQLite: {e}")
            raise EnergySourceError(f"DB error updating energy source {energy_source.id}: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, energy_source_id: EntityId) -> None:
        """Remove an energy source from the SQLite database."""
        self.logger.debug(f"Removing energy source {energy_source_id} from SQLite.")

        sql = "DELETE FROM energy_sources WHERE id = ?"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (energy_source_id,))
                if cursor.rowcount == 0:
                    raise EnergySourceNotFoundError(f"No energy source found with ID {energy_source_id} for removal.")
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing energy source {energy_source_id}: {e}")
            raise EnergySourceError(f"DB error removing energy source {energy_source_id}: {e}") from e
        finally:
            if conn:
                conn.close()


class InMemoryEnergyMonitorRepository(EnergyMonitorRepository):
    """In-Memory implementation for the Energy Monitor Repository."""

    def __init__(
        self,
        initial_energy_monitors: Optional[Dict[EntityId, EnergyMonitor]] = None,
    ):
        self._energy_monitors: Dict[EntityId, EnergyMonitor] = (
            copy.deepcopy(initial_energy_monitors) if initial_energy_monitors else {}
        )

    def add(self, energy_monitor: EnergyMonitor) -> None:
        """Add an energy monitor to the In-Memory repository."""
        if energy_monitor.id in self._energy_monitors:
            # Handle update or raise error depending on desired behavior
            print(f"Warning: Energy Monitor {energy_monitor.id} already exists, overwriting.")
        self._energy_monitors[energy_monitor.id] = copy.deepcopy(energy_monitor)

    def get_by_id(self, energy_monitor_id: EntityId) -> Optional[EnergyMonitor]:
        """Get an energy monitor by ID from the In-Memory repository."""
        return copy.deepcopy(self._energy_monitors.get(energy_monitor_id))

    def get_all(self) -> List[EnergyMonitor]:
        """Get all energy monitors from the In-Memory repository."""
        return [copy.deepcopy(e) for e in self._energy_monitors.values()]

    def update(self, energy_monitor: EnergyMonitor) -> None:
        """Update an energy monitor in the In-Memory repository."""
        if energy_monitor.id in self._energy_monitors:
            self._energy_monitors[energy_monitor.id] = copy.deepcopy(energy_monitor)

    def remove(self, energy_monitor_id: EntityId) -> None:
        """Remove an energy monitor from the In-Memory repository."""
        if energy_monitor_id in self._energy_monitors:
            del self._energy_monitors[energy_monitor_id]

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[EnergyMonitor]:
        """Get all energy monitors associated with a specific external service ID."""
        return [
            copy.deepcopy(em) for em in self._energy_monitors.values() if em.external_service_id == external_service_id
        ]


class SqliteEnergyMonitorRepository(EnergyMonitorRepository):
    """SQLite implementation for the Energy Monitor Repository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the tables for the Energy Monitor Repository."""
        self.logger.debug(f"Ensuring SQLite tables exist for Energy Monitor Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS energy_monitors (
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
                cursor = conn.cursor()
                for statement in sql_statements:
                    cursor.execute(statement)

                self.logger.debug("Energy Monitors tables checked/created successfully.")

        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise EnergySourceError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _deserialize_config(self, adapter_type: EnergyMonitorAdapter, config_json: str) -> EnergyMonitorConfig:
        """Deserialize a JSON string into EnergyMonitorConfig object."""
        data: dict = json.loads(config_json)

        if adapter_type not in ENERGY_MONITOR_CONFIG_TYPE_MAP:
            raise EnergyMonitorConfigurationError(
                f"Error reading EnergyMonitor configuration. Invalid type '{adapter_type}'"
            )

        config_class: Optional[type[EnergyMonitorConfig]] = ENERGY_MONITOR_CONFIG_TYPE_MAP.get(adapter_type)
        if not config_class:
            raise EnergyMonitorConfigurationError(f"Error creating EnergyMonitor configuration. Type '{adapter_type}'")

        config_instance = config_class.from_dict(data)
        if not isinstance(config_instance, EnergyMonitorConfig):
            raise EnergyMonitorConfigurationError(
                f"Deserialized config is not of type EnergyMonitorConfig for adapter type {adapter_type}."
            )
        return config_instance

    def _row_to_energy_monitor(self, row: sqlite3.Row) -> Optional[EnergyMonitor]:
        """Convert a SQLite row to an EnergyMonitor object."""
        if not row:
            return None
        try:
            energy_monitor_adapter_type = EnergyMonitorAdapter(row["adapter_type"])

            # Deserialize the config from the database row
            config = self._deserialize_config(energy_monitor_adapter_type, row["config"])

            return EnergyMonitor(
                id=EntityId(row["id"]),
                name=row["name"],
                adapter_type=energy_monitor_adapter_type,
                config=config,
                external_service_id=(EntityId(row["external_service_id"]) if row["external_service_id"] else None),
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing EnergyMonitor from DB row: {row}. Error: {e}")
            return None

    def add(self, energy_monitor: EnergyMonitor) -> None:
        """Add an energy monitor to the SQLite database."""
        self.logger.debug(f"Adding energy monitor {energy_monitor.id} to SQLite.")

        sql = """
            INSERT INTO energy_monitors (id, name, adapter_type, config, external_service_id)
            VALUES (?, ?, ?, ?, ?)
        """
        conn = self._db.get_connection()
        try:
            # Serialize the config to JSON for storage
            config_json: str = ""
            if energy_monitor.config:
                config_json = json.dumps(energy_monitor.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        energy_monitor.id,
                        energy_monitor.name,
                        energy_monitor.adapter_type.value,
                        config_json,
                        energy_monitor.external_service_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Error adding energy monitor {energy_monitor.id} to SQLite: {e}")
            # Could mean that the ID already exists
            raise EnergySourceAlreadyExistsError(
                f"Energy Monitor with ID {energy_monitor.id} already exists or constraint violation: {e}"
            ) from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding energy monitor {energy_monitor.id}: {e}")
            raise EnergySourceError(f"DB error adding energy monitor: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, energy_monitor_id: EntityId) -> Optional[EnergyMonitor]:
        """Get an energy monitor by ID from the SQLite database."""
        self.logger.debug(f"Getting energy monitor {energy_monitor_id} from SQLite.")

        sql = "SELECT * FROM energy_monitors WHERE id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (energy_monitor_id,))
            row = cursor.fetchone()
            return self._row_to_energy_monitor(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting energy monitor {energy_monitor_id}: {e}")
            return None  # Or raise exception? Returning None is more forgiving
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[EnergyMonitor]:
        """Get all energy monitors from the SQLite database."""
        self.logger.debug("Getting all energy monitors from SQLite.")

        sql = "SELECT * FROM energy_monitors"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            energy_monitors = []
            for row in rows:
                energy_monitor = self._row_to_energy_monitor(row)
                if energy_monitor:
                    energy_monitors.append(energy_monitor)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all energy monitors: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return energy_monitors

    def update(self, energy_monitor: EnergyMonitor) -> None:
        """Update an energy monitor in the SQLite database."""
        self.logger.debug(f"Updating energy monitor {energy_monitor.id} in SQLite.")

        sql = """
            UPDATE energy_monitors
            SET name = ?, adapter_type = ?, config = ?, external_service_id = ?
            WHERE id = ?
        """
        conn = self._db.get_connection()
        try:
            # Serialize the config to JSON for storage
            config_json: str = ""
            if energy_monitor.config:
                config_json = json.dumps(energy_monitor.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        energy_monitor.name,
                        energy_monitor.adapter_type.value,
                        config_json,
                        energy_monitor.external_service_id,
                        energy_monitor.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise EnergySourceNotFoundError(f"No energy monitor found with ID {energy_monitor.id} for update.")
        except sqlite3.Error as e:
            self.logger.error(f"Error updating energy monitor {energy_monitor.id} in SQLite: {e}")
            raise EnergySourceError(f"DB error updating energy monitor {energy_monitor.id}: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, energy_monitor_id: EntityId) -> None:
        """Remove an energy monitor from the SQLite database."""
        self.logger.debug(f"Removing energy monitor {energy_monitor_id} from SQLite.")

        sql = "DELETE FROM energy_monitors WHERE id = ?"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (energy_monitor_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(f"Attempt to remove non-existent energy monitor with ID {energy_monitor_id}.")
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing energy monitor {energy_monitor_id}: {e}")
            raise EnergyMonitorError(f"DB error removing energy monitor {energy_monitor_id}: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[EnergyMonitor]:
        """Get all energy monitors associated with a specific external service ID."""
        self.logger.debug(f"Getting energy monitors for external service {external_service_id} from SQLite.")

        sql = "SELECT * FROM energy_monitors WHERE external_service_id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (external_service_id,))
            rows = cursor.fetchall()
            energy_monitors = []
            for row in rows:
                energy_monitor = self._row_to_energy_monitor(row)
                if energy_monitor:
                    energy_monitors.append(energy_monitor)
            return energy_monitors
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting energy monitors for external service {external_service_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()
