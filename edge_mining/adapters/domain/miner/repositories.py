"""Repositories for the Miner domain."""

import copy
import json
import sqlite3
from typing import Any, Dict, List, Optional

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.exceptions import ConfigurationError
from edge_mining.domain.miner.common import MinerControllerAdapter, MinerStatus
from edge_mining.domain.miner.entities import Miner, MinerController
from edge_mining.domain.miner.exceptions import (
    MinerControllerAlreadyExistsError,
    MinerControllerConfigurationError,
    MinerControllerError,
    MinerControllerNotFoundError,
    MinerError,
)
from edge_mining.domain.miner.ports import MinerControllerRepository, MinerRepository
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.shared.adapter_maps.miner import MINER_CONTROLLER_CONFIG_TYPE_MAP
from edge_mining.shared.interfaces.config import MinerControllerConfig

# Simple In-Memory implementation for testing and basic use


class InMemoryMinerRepository(MinerRepository):
    """In-Memory implementation for the Miner Repository."""

    def __init__(self, initial_miners: Optional[Dict[EntityId, Miner]] = None):
        self._miners: Dict[EntityId, Miner] = copy.deepcopy(initial_miners) if initial_miners else {}

    def add(self, miner: Miner) -> None:
        """Add a miner to the In-Memory repository."""
        if miner.id in self._miners:
            # Handle update or raise error depending on desired behavior
            print(f"Warning: Miner {miner.id} already exists, overwriting.")
        self._miners[miner.id] = copy.deepcopy(miner)

    def get_by_id(self, miner_id: EntityId) -> Optional[Miner]:
        """Get a miner by ID from the In-Memory repository."""
        return copy.deepcopy(self._miners.get(miner_id))

    def get_all(self) -> List[Miner]:
        """Get all miners from the In-Memory repository."""
        return [copy.deepcopy(m) for m in self._miners.values()]

    def update(self, miner: Miner) -> None:
        """Update a miner in the In-Memory repository."""
        if miner.id not in self._miners:
            raise ValueError(f"Miner {miner.id} not found for update.")
        self._miners[miner.id] = copy.deepcopy(miner)

    def remove(self, miner_id: EntityId) -> None:
        """Remove a miner from the In-Memory repository."""
        if miner_id in self._miners:
            del self._miners[miner_id]

    def get_by_controller_id(self, controller_id: EntityId) -> List[Miner]:
        """Get all miners associated with a specific controller ID."""
        return (
            [copy.deepcopy(m) for m in self._miners.values() if m.controller_id == controller_id]
            if controller_id
            else []
        )


class SqliteMinerRepository(MinerRepository):
    """SQLite implementation for the Miner Repository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables for the Miner domain if they do not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for Miner Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS miners (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                hash_rate TEXT, -- JSON object of HashRate dict
                hash_rate_max TEXT, -- JSON object of HashRate dict
                power_consumption REAL,
                power_consumption_max REAL,
                controller_id TEXT -- Foreign key to miner controller
            );
            """
        ]

        conn = self._db.get_connection()

        try:
            with conn:
                cursor = conn.cursor()
                for statement in sql_statements:
                    cursor.execute(statement)

                self.logger.debug("Miners tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise ConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _dict_to_hashrate(self, data: Dict[str, Any]) -> HashRate:
        """Deserialize a dictionary (from JSON) into an HashRate object."""
        return HashRate(value=float(data["value"]), unit=data["unit"])

    def _hashrate_to_dict(self, hash_rate: Optional[HashRate]) -> Dict[str, Any]:
        """Serializes an HashRate object into a dictionary for JSON."""
        return {
            "value": hash_rate.value if hash_rate else 0,
            "unit": hash_rate.unit if hash_rate else "TH/s",
        }

    def _row_to_miner(self, row: sqlite3.Row) -> Optional[Miner]:
        """Deserialize a row from the database into a Miner object."""
        if not row:
            return None
        try:
            # Deserialize hash_rate from the database row
            hash_rate_data = json.loads(row["hash_rate"]) if row["hash_rate"] else None
            hash_rate_max_data = json.loads(row["hash_rate_max"]) if row["hash_rate_max"] else None

            hash_rate = self._dict_to_hashrate(hash_rate_data) if hash_rate_data else None
            hash_rate_max = self._dict_to_hashrate(hash_rate_max_data) if hash_rate_max_data else None

            return Miner(
                id=EntityId(row["id"]),
                name=row["name"] if row["name"] is not None else "",
                status=MinerStatus(row["status"]),
                active=(row["active"] == 1 if row["active"] is not None else False),
                hash_rate=hash_rate,
                hash_rate_max=hash_rate_max,
                power_consumption=(Watts(row["power_consumption"]) if row["power_consumption"] is not None else None),
                power_consumption_max=(
                    Watts(row["power_consumption_max"]) if row["power_consumption_max"] is not None else None
                ),
                controller_id=(EntityId(row["controller_id"]) if row["controller_id"] else None),
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing Miner from DB row: {row}. Error: {e}")
            return None

    def add(self, miner: Miner) -> None:
        """Add a miner to the SQLite database."""
        self.logger.debug(f"Adding miner {miner.id} to SQLite.")

        sql = """
            INSERT INTO miners (id, name, status, active, hash_rate, hash_rate_max, power_consumption,
            power_consumption_max, controller_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._db.get_connection()
        try:
            # Serialize hash_rate to JSON for storage
            hash_rate_json = json.dumps(self._hashrate_to_dict(miner.hash_rate))
            hash_rate_max_json = json.dumps(self._hashrate_to_dict(miner.hash_rate_max))

            with conn:
                conn.execute(
                    sql,
                    (
                        miner.id,
                        miner.name,
                        miner.status.value,
                        miner.active,
                        hash_rate_json,
                        hash_rate_max_json,
                        (float(miner.power_consumption) if miner.power_consumption is not None else 0.0),
                        (float(miner.power_consumption_max) if miner.power_consumption_max is not None else 0.0),
                        miner.controller_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding miner {miner.id}: {e}")
            # Could mean that the ID already exists
            raise MinerError(f"Miner with ID {miner.id} already exists or constraint violation: {e}") from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding miner {miner.id}: {e}")
            raise MinerError(f"DB error adding miner: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, miner_id: EntityId) -> Optional[Miner]:
        """Get a miner by ID from the SQLite database."""
        self.logger.debug(f"Getting miner {miner_id} from SQLite.")

        sql = "SELECT * FROM miners WHERE id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (miner_id,))
            row = cursor.fetchone()
            return self._row_to_miner(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting miner {miner_id}: {e}")
            return None  # Or raise exception? Returning None is more forgiving
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[Miner]:
        """Get all miners from the SQLite database."""
        self.logger.debug("Getting all miners from SQLite.")

        sql = "SELECT * FROM miners"
        conn = self._db.get_connection()
        miners = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                miner = self._row_to_miner(row)
                if miner:
                    miners.append(miner)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all miners: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return miners

    def update(self, miner: Miner) -> None:
        """Update a miner in the SQLite database."""
        self.logger.debug(f"Updating miner {miner.id} in SQLite.")

        sql = """
            UPDATE miners
            SET name = ?, status = ?, active = ?, hash_rate = ?, hash_rate_max = ?, power_consumption = ?,
            power_consumption_max = ?, controller_id = ?
            WHERE id = ?
        """
        conn = self._db.get_connection()
        try:
            # Serialize hash_rate to JSON for storage
            hash_rate_json = json.dumps(self._hashrate_to_dict(miner.hash_rate))
            hash_rate_max_json = json.dumps(self._hashrate_to_dict(miner.hash_rate_max))

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        miner.name,
                        miner.status.value,
                        miner.active,
                        hash_rate_json,
                        hash_rate_max_json,
                        (float(miner.power_consumption) if miner.power_consumption is not None else 0.0),
                        (float(miner.power_consumption_max) if miner.power_consumption_max is not None else 0.0),
                        miner.controller_id,
                        miner.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise MinerError(f"No miner found with ID {miner.id} for update.")
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating miner {miner.id}: {e}")
            raise MinerError(f"DB error updating miner: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, miner_id: EntityId) -> None:
        """Remove a miner from the SQLite database."""
        self.logger.debug(f"Removing miner {miner_id} from SQLite.")

        sql = "DELETE FROM miners WHERE id = ?"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (miner_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(f"Attempt to remove non-existent miner with ID {miner_id}.")
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing miner {miner_id}: {e}")
            raise MinerError(f"DB error removing miner: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_controller_id(self, controller_id: EntityId) -> List[Miner]:
        """Get all miners associated with a specific controller ID."""
        self.logger.debug(f"Getting miners by controller ID {controller_id} from SQLite.")

        sql = "SELECT * FROM miners WHERE controller_id = ?"
        conn = self._db.get_connection()
        miners = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (controller_id,))
            rows = cursor.fetchall()
            for row in rows:
                miner = self._row_to_miner(row)
                if miner:
                    miners.append(miner)
            return miners
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting miners by controller ID {controller_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()


class InMemoryMinerControllerRepository(MinerControllerRepository):
    """In-Memory implementation for the Miner Controller Repository."""

    def __init__(
        self,
        initial_miner_controllers: Optional[Dict[EntityId, MinerController]] = None,
    ):
        self._miner_controllers: Dict[EntityId, MinerController] = (
            copy.deepcopy(initial_miner_controllers) if initial_miner_controllers else {}
        )

    def add(self, miner_controller: MinerController) -> None:
        """Add a miner controller to the In-Memory repository."""
        if miner_controller.id in self._miner_controllers:
            # Handle update or raise error depending on desired behavior
            print(f"Warning: Miner Controller {miner_controller.id} already exists, overwriting.")
        self._miner_controllers[miner_controller.id] = copy.deepcopy(miner_controller)

    def get_by_id(self, miner_controller_id: EntityId) -> Optional[MinerController]:
        """Get a miner controller by ID from the In-Memory repository."""
        return copy.deepcopy(self._miner_controllers.get(miner_controller_id))

    def get_all(self) -> List[MinerController]:
        """Get all miner controllers from the In-Memory repository."""
        return [copy.deepcopy(m) for m in self._miner_controllers.values()]

    def update(self, miner_controller: MinerController) -> None:
        """Update a miner controller in the In-Memory repository."""
        if miner_controller.id not in self._miner_controllers:
            raise ValueError(f"Miner Controller {miner_controller.id} not found for update.")
        self._miner_controllers[miner_controller.id] = copy.deepcopy(miner_controller)

    def remove(self, miner_controller_id: EntityId) -> None:
        """Remove a miner controller from the In-Memory repository."""
        if miner_controller_id in self._miner_controllers:
            del self._miner_controllers[miner_controller_id]

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[MinerController]:
        """Get all miner controllers associated with a specific external service ID."""
        return (
            [
                copy.deepcopy(mc)
                for mc in self._miner_controllers.values()
                if mc.external_service_id == external_service_id
            ]
            if external_service_id
            else []
        )


class SqliteMinerControllerRepository(MinerControllerRepository):
    """SQLite implementation for the Miner Controller Repository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables for the Miner Controller if they do not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for Miner Controller Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS miner_controllers (
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

                self.logger.debug("Miner Controllers tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise ConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _deserialize_config(self, adapter_type: MinerControllerAdapter, config_json: str) -> MinerControllerConfig:
        """Deserialize a JSON string into MinerControllerConfig object."""
        data: dict = json.loads(config_json)

        if adapter_type not in MINER_CONTROLLER_CONFIG_TYPE_MAP:
            raise MinerControllerConfigurationError(
                f"Error reading MinerController configuration. Invalid type '{adapter_type}'"
            )

        config_class: Optional[type[MinerControllerConfig]] = MINER_CONTROLLER_CONFIG_TYPE_MAP.get(adapter_type)
        if not config_class:
            raise MinerControllerConfigurationError(
                f"Error creating MinerController configuration. Type '{adapter_type}'"
            )

        config_instance = config_class.from_dict(data)
        if not isinstance(config_instance, MinerControllerConfig):
            raise MinerControllerConfigurationError(
                f"Deserialized config is not of type MinerControllerConfig for adapter type {adapter_type}."
            )
        return config_instance

    def _row_to_miner_controller(self, row: sqlite3.Row) -> Optional[MinerController]:
        """Deserialize a row from the database into a MinerController object."""
        if not row:
            return None
        try:
            miner_controller_type = MinerControllerAdapter(row["adapter_type"])

            # Deserialize the config from the database row
            config = self._deserialize_config(miner_controller_type, row["config"])

            return MinerController(
                id=EntityId(row["id"]),
                name=row["name"],
                adapter_type=miner_controller_type,
                config=config,
                external_service_id=(EntityId(row["external_service_id"]) if row["external_service_id"] else None),
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing MinerController from DB row: {row}. Error: {e}")
            return None

    def add(self, miner_controller: MinerController) -> None:
        """Add a miner controller to the SQLite database."""
        self.logger.debug(f"Adding miner controller {miner_controller.id} to SQLite.")

        sql = """
            INSERT INTO miner_controllers (id, name, adapter_type, config, external_service_id)
            VALUES (?, ?, ?, ?, ?)
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if miner_controller.config:
                config_json = json.dumps(miner_controller.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        miner_controller.id,
                        miner_controller.name,
                        miner_controller.adapter_type.value,
                        config_json,
                        miner_controller.external_service_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding miner controller {miner_controller.id}: {e}")
            # Could mean that the ID already exists
            raise MinerControllerAlreadyExistsError(
                f"Miner Controller with ID {miner_controller.id} already exists or constraint violation: {e}"
            ) from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding miner controller {miner_controller.id}: {e}")
            raise MinerControllerError(f"DB error adding miner controller: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, miner_controller_id: EntityId) -> Optional[MinerController]:
        """Get a miner controller by ID from the SQLite database."""
        self.logger.debug(f"Getting miner controller {miner_controller_id} from SQLite.")

        sql = "SELECT * FROM miner_controllers WHERE id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (miner_controller_id,))
            row = cursor.fetchone()
            return self._row_to_miner_controller(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting miner controller {miner_controller_id}: {e}")
            return None  # Or raise exception? Returning None is more forgiving
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[MinerController]:
        """Get all miner controllers from the SQLite database."""
        self.logger.debug("Getting all miner controllers from SQLite.")

        sql = "SELECT * FROM miner_controllers"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            miner_controllers = []
            for row in rows:
                miner_controller = self._row_to_miner_controller(row)
                if miner_controller:
                    miner_controllers.append(miner_controller)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all miner controllers: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return miner_controllers

    def update(self, miner_controller: MinerController) -> None:
        """Update a miner controller in the SQLite database."""
        self.logger.debug(f"Updating miner controller {miner_controller.id} in SQLite.")

        sql = """
            UPDATE miner_controllers
            SET name = ?, adapter_type = ?, config = ?, external_service_id = ?
            WHERE id = ?
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if miner_controller.config:
                config_json = json.dumps(miner_controller.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        miner_controller.name,
                        miner_controller.adapter_type.value,
                        config_json,
                        miner_controller.external_service_id,
                        miner_controller.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise MinerControllerNotFoundError(
                        f"No miner controller found with ID {miner_controller.id} for update."
                    )
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating miner controller {miner_controller.id}: {e}")
            raise MinerControllerError(f"DB error updating miner controller: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, miner_controller_id: EntityId) -> None:
        """Remove a miner controller from the SQLite database."""
        self.logger.debug(f"Removing miner controller {miner_controller_id} from SQLite.")

        sql = "DELETE FROM miner_controllers WHERE id = ?"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (miner_controller_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(
                        f"Attempt to remove non-existent miner controller with ID {miner_controller_id}."
                    )
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing miner controller {miner_controller_id}: {e}")
            raise MinerControllerError(f"DB error removing miner controller: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[MinerController]:
        """Get all miner controllers associated with a specific external service ID."""
        self.logger.debug(f"Getting miner controllers for external service ID {external_service_id} from SQLite.")

        sql = "SELECT * FROM miner_controllers WHERE external_service_id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (external_service_id,))
            rows = cursor.fetchall()
            miner_controllers = []
            for row in rows:
                miner_controller = self._row_to_miner_controller(row)
                if miner_controller:
                    miner_controllers.append(miner_controller)
            return miner_controllers
        except sqlite3.Error as e:
            self.logger.error(
                f"SQLite error getting miner controllers by external service ID {external_service_id}: {e}"
            )
            return []
        finally:
            if conn:
                conn.close()
