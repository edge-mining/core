"""Repositories for Forecast Domain."""

import json
import sqlite3
from typing import List, Optional

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId
from edge_mining.domain.exceptions import ConfigurationError
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.domain.forecast.entities import ForecastProvider
from edge_mining.domain.forecast.exceptions import (
    ForecastProviderAlreadyExistsError,
    ForecastProviderConfigurationError,
    ForecastProviderError,
    ForecastProviderNotFoundError,
)
from edge_mining.domain.forecast.ports import ForecastProviderRepository
from edge_mining.shared.adapter_maps.forecast import FORECAST_PROVIDER_CONFIG_TYPE_MAP
from edge_mining.shared.interfaces.config import ForecastProviderConfig

# Simple In-Memory implementation for testing and basic use


class InMemoryForecastProviderRepository(ForecastProviderRepository):
    """In-memory implementation of ForecastProviderRepository for testing purposes."""

    def __init__(self):
        self._forecast_providers: List[ForecastProvider] = []

    def add(self, forecast_provider: ForecastProvider) -> None:
        self._forecast_providers.append(forecast_provider)

    def get_by_id(self, forecast_provider_id: EntityId) -> Optional[ForecastProvider]:
        for forecast_provider in self._forecast_providers:
            if forecast_provider.id == forecast_provider_id:
                return forecast_provider
        return None

    def get_all(self) -> List[ForecastProvider]:
        return self._forecast_providers

    def update(self, forecast_provider: ForecastProvider) -> None:
        for i, existing_forecast_provider in enumerate(self._forecast_providers):
            if existing_forecast_provider.id == forecast_provider.id:
                self._forecast_providers[i] = forecast_provider
                return

    def remove(self, forecast_provider_id: EntityId) -> None:
        self._forecast_providers = [n for n in self._forecast_providers if n.id != forecast_provider_id]

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[ForecastProvider]:
        """Get all forecast providers associated with a specific external service ID."""
        return (
            [fp for fp in self._forecast_providers if fp.external_service_id == external_service_id]
            if external_service_id
            else []
        )


class SqliteForecastProviderRepository(ForecastProviderRepository):
    """SQLite implementation of ForecastProviderRepository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary table for the Forecast Provider if it does not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for Forecast Provider Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS forecast_providers (
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

                self.logger.debug("Forecast providers tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise ConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _deserialize_config(self, adapter_type: ForecastProviderAdapter, config_json: str) -> ForecastProviderConfig:
        """Deserialize a JSON string into ForecastProviderConfig object."""
        data: dict = json.loads(config_json)

        if adapter_type not in FORECAST_PROVIDER_CONFIG_TYPE_MAP:
            raise ForecastProviderConfigurationError(
                f"Error reading ForecastProvider configuration. Invalid type '{adapter_type}'"
            )

        config_class: Optional[type[ForecastProviderConfig]] = FORECAST_PROVIDER_CONFIG_TYPE_MAP.get(adapter_type)
        if not config_class:
            raise ForecastProviderConfigurationError(
                f"Error creating ForecastProvider configuration. Type '{adapter_type}'"
            )

        config_instance = config_class.from_dict(data)
        if not isinstance(config_instance, ForecastProviderConfig):
            raise ForecastProviderConfigurationError(
                f"Deserialized config is not of type ForecastProviderConfig for adapter type {adapter_type}."
            )
        return config_instance

    def _row_to_forecast_provider(self, row: sqlite3.Row) -> Optional[ForecastProvider]:
        """Deserialize a row from the database into a ForecastProvider object."""
        if not row:
            return None
        try:
            forecast_provider_type = ForecastProviderAdapter(row["adapter_type"])

            # Deserialize config from the database row
            config = self._deserialize_config(forecast_provider_type, row["config"])

            return ForecastProvider(
                id=EntityId(row["id"]),
                name=row["name"],
                adapter_type=forecast_provider_type,
                config=config,
                external_service_id=(EntityId(row["external_service_id"]) if row["external_service_id"] else None),
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing ForecastProvider from DB row: {row}. Error: {e}")
            return None

    def add(self, forecast_provider: ForecastProvider) -> None:
        """Add a new forecast provider to the repository."""
        self.logger.debug(f"Adding forecast provider {forecast_provider.id} to SQLite repository.")
        sql = """
            INSERT INTO forecast_providers (id, name, adapter_type, config, external_service_id)
            VALUES (?, ?, ?, ?, ?);
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if forecast_provider.config:
                config_json = json.dumps(forecast_provider.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        forecast_provider.id,
                        forecast_provider.name,
                        forecast_provider.adapter_type.value,
                        config_json,
                        forecast_provider.external_service_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding forecast provider {forecast_provider.id}: {e}")
            # Could mean that the ID already exists
            raise ForecastProviderAlreadyExistsError(
                f"forecast provider with ID {forecast_provider.id} already exists or constraint violation: {e}"
            ) from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding forecast provider {forecast_provider.id}: {e}")
            raise ForecastProviderError(f"DB error adding forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, forecast_provider_id: EntityId) -> Optional[ForecastProvider]:
        """Retrieve a forecast provider by its ID."""
        self.logger.debug(f"Retrieving forecast provider {forecast_provider_id} from SQLite repository.")
        sql = "SELECT * FROM forecast_providers WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (forecast_provider_id,))
            row = cursor.fetchone()
            return self._row_to_forecast_provider(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving forecast provider {forecast_provider_id}: {e}")
            raise ForecastProviderNotFoundError(f"DB error retrieving forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[ForecastProvider]:
        """Retrieve all forecast providers from the repository."""
        self.logger.debug("Retrieving all forecast providers from SQLite repository.")
        sql = "SELECT * FROM forecast_providers;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            forecast_providers = []
            for row in rows:
                forecast_provider = self._row_to_forecast_provider(row)
                if forecast_provider:
                    forecast_providers.append(forecast_provider)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving all forecast providers: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return forecast_providers

    def update(self, forecast_provider: ForecastProvider) -> None:
        """Update an existing forecast provider in the repository."""
        self.logger.debug(f"Updating forecast provider {forecast_provider.id} in SQLite repository.")
        sql = """
            UPDATE forecast_providers
            SET name = ?, adapter_type = ?, config = ?, external_service_id = ?
            WHERE id = ?;
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if forecast_provider.config:
                config_json = json.dumps(forecast_provider.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        forecast_provider.name,
                        forecast_provider.adapter_type.value,
                        config_json,
                        forecast_provider.external_service_id,
                        forecast_provider.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ForecastProviderNotFoundError(f"Forecast Provider with ID {forecast_provider.id} not found.")
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating forecast provider {forecast_provider.id}: {e}")
            raise ForecastProviderError(f"DB error updating forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, forecast_provider_id: EntityId) -> None:
        """Remove a forecast provider from the repository."""
        self.logger.debug(f"Removing forecast provider {forecast_provider_id} from SQLite repository.")
        sql = "DELETE FROM forecast_providers WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (forecast_provider_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(f"Attempted to remove non-existent forecast provider {forecast_provider_id}.")
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing forecast provider {forecast_provider_id}: {e}")
            raise ForecastProviderError(f"DB error removing forecast provider: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_external_service_id(self, external_service_id: EntityId) -> List[ForecastProvider]:
        """Get all forecast providers associated with a specific external service ID."""
        self.logger.debug(
            f"Retrieving forecast providers for external service {external_service_id} from SQLite repository."
        )
        sql = "SELECT * FROM forecast_providers WHERE external_service_id = ?;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (external_service_id,))
            rows = cursor.fetchall()
            forecast_providers = []
            for row in rows:
                forecast_provider = self._row_to_forecast_provider(row)
                if forecast_provider:
                    forecast_providers.append(forecast_provider)
            return forecast_providers
        except sqlite3.Error as e:
            self.logger.error(
                f"SQLite error retrieving forecast providers for external service {external_service_id}: {e}"
            )
            return []
        finally:
            if conn:
                conn.close()
