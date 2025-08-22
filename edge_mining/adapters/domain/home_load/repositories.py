"""Repositories for the Home loads domain."""

import copy
import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId
from edge_mining.domain.exceptions import ConfigurationError
from edge_mining.domain.home_load.aggregate_roots import HomeLoadsProfile
from edge_mining.domain.home_load.common import HomeForecastProviderAdapter
from edge_mining.domain.home_load.entities import HomeForecastProvider, LoadDevice
from edge_mining.domain.home_load.exceptions import (
    HomeForecastProviderAlreadyExistsError,
    HomeForecastProviderError,
    HomeForecastProviderNotFoundError,
    HomeForecastProviderConfigurationError,
)
from edge_mining.domain.home_load.ports import (
    HomeForecastProviderRepository,
    HomeLoadsProfileRepository,
)
from edge_mining.shared.adapter_maps.home_load import (
    HOME_FORECAST_PROVIDER_CONFIG_TYPE_MAP,
)
from edge_mining.shared.interfaces.config import HomeForecastProviderConfig

# Simple In-Memory implementation for testing and basic use


class InMemoryHomeLoadsProfileRepository(HomeLoadsProfileRepository):
    """In-Memory implementation for the Home Loads Profile Repository."""

    def __init__(self, initial_profile: Optional[HomeLoadsProfile] = None):
        self._profile: Optional[HomeLoadsProfile] = copy.deepcopy(initial_profile)

    def get_profile(self) -> Optional[HomeLoadsProfile]:
        return copy.deepcopy(self._profile)

    def save_profile(self, profile: HomeLoadsProfile) -> None:
        self._profile = copy.deepcopy(profile)


class SqliteHomeLoadsProfileRepository(HomeLoadsProfileRepository):
    """SQLite implementation for the Home Loads Profile Repository."""

    # fixed UUID for the default profile
    _DEFAULT_PROFILE_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables for the Home Load domain if they do not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for Home Loads Profile Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS home_profiles (
                id TEXT PRIMARY KEY, -- e.g., fixed UUID for default profile
                name TEXT NOT NULL,
                devices_json TEXT -- JSON Dict[EntityId_str, LoadDevice_dict]
            );
            """
        ]

        conn = self._db.get_connection()

        try:
            with conn:
                cursor = conn.cursor()
                for statement in sql_statements:
                    cursor.execute(statement)

                self.logger.debug("Home Loads Profile tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise ConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _device_to_dict(self, device: LoadDevice) -> Dict[str, Any]:
        return {"id": str(device.id), "name": device.name, "type": device.type}

    def _dict_to_device(self, data: Dict[str, Any]) -> LoadDevice:
        """Convert a dictionary to a LoadDevice."""
        return LoadDevice(id=EntityId(uuid.UUID(data["id"])), name=data["name"], type=data["type"])

    def _row_to_profile(self, row: sqlite3.Row) -> Optional[HomeLoadsProfile]:
        """Convert a row to a HomeLoadsProfile."""
        if not row:
            return None
        try:
            devices_data: Dict = json.loads(row["devices_json"] or "{}")
            devices = {
                EntityId(uuid.UUID(id_str)): self._dict_to_device(dev_dict) for id_str, dev_dict in devices_data.items()
            }
            return HomeLoadsProfile(id=row["id"], name=row["name"], devices=devices)  # UUID
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error deserializing HomeLoadsProfile from DB line: {dict(row)}. Error: {e}")
            return None

    def get_profile(self) -> Optional[HomeLoadsProfile]:
        """Get the home load profile from SQLite."""
        self.logger.debug("Getting home load profile from SQLite.")
        sql = "SELECT * FROM home_profiles WHERE id = ?"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (self._DEFAULT_PROFILE_UUID,))
            row = cursor.fetchone()
            if row:
                return self._row_to_profile(row)
            else:
                self.logger.info("No home load profile found in DB, returning None.")
                return None
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting home profile: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def save_profile(self, profile: HomeLoadsProfile) -> None:
        """Save the home load profile to SQLite."""
        self.logger.debug(f"Saving home load profile '{profile.name}' to SQLite.")
        sql = "INSERT OR REPLACE INTO home_profiles (id, name, devices_json) VALUES (?, ?, ?)"
        conn = self._db.get_connection()
        try:
            # Serialize the dictionary of devices
            devices_json = json.dumps({str(id): self._device_to_dict(dev) for id, dev in profile.devices.items()})
            with conn:
                # Always use the fixed UUID for the default profile
                # default
                conn.execute(
                    sql,
                    (self._DEFAULT_PROFILE_UUID, profile.name, devices_json),
                )
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error saving home profile: {e}")
            raise ConfigurationError(f"DB error saving home profile: {e}") from e
        finally:
            if conn:
                conn.close()


class InMemoryHomeForecastProviderRepository(HomeForecastProviderRepository):
    """In-memory implementation of HomeForecastProviderRepository for testing purposes."""

    def __init__(self):
        self._home_forecast_providers: List[HomeForecastProvider] = []

    def add(self, home_forecast_provider: HomeForecastProvider) -> None:
        self._home_forecast_providers.append(home_forecast_provider)

    def get_by_id(self, home_forecast_provider_id: EntityId) -> Optional[HomeForecastProvider]:
        for home_forecast_provider in self._home_forecast_providers:
            if home_forecast_provider.id == home_forecast_provider_id:
                return home_forecast_provider
        return None

    def get_all(self) -> List[HomeForecastProvider]:
        return self._home_forecast_providers

    def update(self, home_forecast_provider: HomeForecastProvider) -> None:
        for i, existing_home_forecast_provider in enumerate(self._home_forecast_providers):
            if existing_home_forecast_provider.id == home_forecast_provider.id:
                self._home_forecast_providers[i] = home_forecast_provider
                return

    def remove(self, home_forecast_provider_id: EntityId) -> None:
        self._home_forecast_providers = [n for n in self._home_forecast_providers if n.id != home_forecast_provider_id]

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[HomeForecastProvider]:
        """Retrieve all home forecast providers linked to a specific external service."""
        return (
            [
                provider
                for provider in self._home_forecast_providers
                if provider.external_service_id == external_service_id
            ]
            if external_service_id
            else []
        )


class SqliteHomeForecastProviderRepository(HomeForecastProviderRepository):
    """SQLite implementation of HomeForecastProviderRepository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary table for the Home Forecast Provider if it does not exist."""
        self.logger.debug(
            f"Ensuring SQLite tables exist for Home Forecast Provider Repository in {self._db.db_path}..."
        )
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS home_forecast_providers (
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

                self.logger.debug("Home Forecast providers tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise ConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _deserialize_config(
        self, adapter_type: HomeForecastProviderAdapter, config_json: str
    ) -> HomeForecastProviderConfig:
        """Deserialize a JSON string into HomeForecastProviderConfig object."""
        data: dict = json.loads(config_json)

        if adapter_type not in HOME_FORECAST_PROVIDER_CONFIG_TYPE_MAP:
            raise HomeForecastProviderNotFoundError(
                f"Error reading HomeForecastProvider configuration. Invalid type '{adapter_type}'"
            )

        config_class: Optional[type[HomeForecastProviderConfig]] = HOME_FORECAST_PROVIDER_CONFIG_TYPE_MAP.get(
            adapter_type
        )
        if not config_class:
            raise HomeForecastProviderNotFoundError(
                f"Error creating HomeForecastProviderConfig configuration. Type '{adapter_type}'"
            )

        config_instance = config_class.from_dict(data)
        if not isinstance(config_instance, HomeForecastProviderConfig):
            raise HomeForecastProviderConfigurationError(
                f"Deserialized config is not of type HomeForecastProviderConfig for adapter type {adapter_type}."
            )
        return config_instance

    def _row_to_home_forecast_provider(self, row: sqlite3.Row) -> Optional[HomeForecastProvider]:
        """Deserialize a row from the database into a HomeForecastProvider object."""
        if not row:
            return None
        try:
            home_forecast_provider_type = HomeForecastProviderAdapter(row["adapter_type"])

            # Deserialize the config from the database row
            config = self._deserialize_config(home_forecast_provider_type, row["config"])

            return HomeForecastProvider(
                id=EntityId(row["id"]),
                name=row["name"],
                adapter_type=home_forecast_provider_type,
                config=config,
                external_service_id=(EntityId(row["external_service_id"]) if row["external_service_id"] else None),
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing HomeForecastProvider from DB row: {row}. Error: {e}")
            return None

    def add(self, home_forecast_provider: HomeForecastProvider) -> None:
        """Add a new home forecast provider to the repository."""
        self.logger.debug(f"Adding forecast provider {home_forecast_provider.id} to SQLite repository.")
        sql = """
            INSERT INTO home_forecast_providers (id, name, adapter_type, config, external_service_id)
            VALUES (?, ?, ?, ?, ?);
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if home_forecast_provider.config:
                config_json = json.dumps(home_forecast_provider.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        home_forecast_provider.id,
                        home_forecast_provider.name,
                        home_forecast_provider.adapter_type.value,
                        config_json,
                        home_forecast_provider.external_service_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding home forecast provider {home_forecast_provider.id}: {e}")
            # Could mean that the ID already exists
            raise HomeForecastProviderAlreadyExistsError(
                f"Home forecast provider with ID {home_forecast_provider.id} "
                f"already exists or constraint violation: {e}"
            ) from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding home forecast provider {home_forecast_provider.id}: {e}")
            raise HomeForecastProviderError(f"DB error adding home forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, home_forecast_provider_id: EntityId) -> Optional[HomeForecastProvider]:
        """Retrieve an home forecast provider by its ID."""
        self.logger.debug(f"Retrieving home forecast provider {home_forecast_provider_id} from SQLite repository.")
        sql = "SELECT * FROM home_forecast_providers WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (home_forecast_provider_id,))
            row = cursor.fetchone()
            return self._row_to_home_forecast_provider(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving home forecast provider {home_forecast_provider_id}: {e}")
            raise HomeForecastProviderNotFoundError(f"DB error retrieving home forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[HomeForecastProvider]:
        """Retrieve all home forecast providers from the repository."""
        self.logger.debug("Retrieving all home forecast providers from SQLite repository.")
        sql = "SELECT * FROM home_forecast_providers;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            home_forecast_providers = []
            for row in rows:
                home_forecast_provider = self._row_to_home_forecast_provider(row)
                if home_forecast_provider:
                    home_forecast_providers.append(home_forecast_provider)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving all home forecast providers: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return home_forecast_providers

    def update(self, home_forecast_provider: HomeForecastProvider) -> None:
        """Update an existing home forecast provider in the repository."""
        self.logger.debug(f"Updating home forecast provider {home_forecast_provider.id} in SQLite repository.")
        sql = """
            UPDATE home_forecast_providers
            SET name = ?, adapter_type = ?, config = ?, external_service_id = ?
            WHERE id = ?;
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json = json.dumps(home_forecast_provider.config)

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        home_forecast_provider.name,
                        home_forecast_provider.adapter_type.value,
                        config_json,
                        home_forecast_provider.external_service_id,
                        home_forecast_provider.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise HomeForecastProviderNotFoundError(
                        f"Home Forecast Provider with ID {home_forecast_provider.id} not found."
                    )
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating home forecast provider {home_forecast_provider.id}: {e}")
            raise HomeForecastProviderError(f"DB error updating home forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, home_forecast_provider_id: EntityId) -> None:
        """Remove an home forecast provider from the repository."""
        self.logger.debug(f"Removing forecast provider {home_forecast_provider_id} from SQLite repository.")
        sql = "DELETE FROM home_forecast_providers WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (home_forecast_provider_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(
                        f"Attempted to remove non-existent home forecast provider {home_forecast_provider_id}."
                    )
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing home forecast provider {home_forecast_provider_id}: {e}")
            raise HomeForecastProviderError(f"DB error removing home forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[HomeForecastProvider]:
        """Retrieve all home forecast providers linked to a specific external service."""
        self.logger.debug(
            "Retrieving home forecast providers linked to external service "
            f"{external_service_id} from SQLite repository."
        )
        sql = "SELECT * FROM home_forecast_providers WHERE external_service_id = ?;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (external_service_id,))
            rows = cursor.fetchall()
            home_forecast_providers = []
            for row in rows:
                home_forecast_provider = self._row_to_home_forecast_provider(row)
                if home_forecast_provider:
                    home_forecast_providers.append(home_forecast_provider)
            return home_forecast_providers
        except sqlite3.Error as e:
            self.logger.error(
                f"SQLite error retrieving home forecast providers by external service ID {external_service_id}: {e}"
            )
            return []
        finally:
            if conn:
                conn.close()
