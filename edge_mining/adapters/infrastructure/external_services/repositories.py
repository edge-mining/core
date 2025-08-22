"""Repositories for External Service."""

import json
import sqlite3
from typing import List, Optional

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId
from edge_mining.domain.exceptions import ConfigurationError
from edge_mining.shared.adapter_maps.external_services import (
    EXTERNAL_SERVICE_CONFIG_TYPE_MAP,
)
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.external_services.exceptions import (
    ExternalServiceAlreadyExistsError,
    ExternalServiceConfigurationError,
    ExternalServiceError,
    ExternalServiceNotFoundError,
)
from edge_mining.shared.external_services.ports import ExternalServiceRepository
from edge_mining.shared.interfaces.config import ExternalServiceConfig

# Simple In-Memory implementation for testing and basic use


class InMemoryExternalServiceRepository(ExternalServiceRepository):
    """In-memory implementation of ExternalServiceRepository for testing purposes."""

    def __init__(self):
        self._external_services: List[ExternalService] = []

    def add(self, external_service: ExternalService) -> None:
        self._external_services.append(external_service)

    def get_by_id(self, external_service_id: EntityId) -> Optional[ExternalService]:
        for external_service in self._external_services:
            if external_service.id == external_service_id:
                return external_service
        return None

    def get_all(self) -> List[ExternalService]:
        return self._external_services

    def update(self, external_service: ExternalService) -> None:
        for i, existing_external_service in enumerate(self._external_services):
            if existing_external_service.id == external_service.id:
                self._external_services[i] = external_service
                return

    def remove(self, external_service_id: EntityId) -> None:
        self._external_services = [n for n in self._external_services if n.id != external_service_id]


class SqliteExternalServiceRepository(ExternalServiceRepository):
    """SQLite implementation of ExternalServiceRepository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary table for the External Service if it does not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for External Service Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS external_services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                adapter_type TEXT NOT NULL,
                config TEXT -- JSON object of config
            );
            """
        ]
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                for statement in sql_statements:
                    cursor.execute(statement)

                self.logger.debug("External services tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise ConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _deserialize_config(self, adapter_type: ExternalServiceAdapter, config_json: str) -> ExternalServiceConfig:
        """Deserialize a JSON string into ExternalServiceConfig object."""
        data: dict = json.loads(config_json)

        if adapter_type not in EXTERNAL_SERVICE_CONFIG_TYPE_MAP:
            raise ExternalServiceConfigurationError(
                f"Error reading External Service configuration. Invalid type '{adapter_type}'"
            )

        config_class: Optional[type[ExternalServiceConfig]] = EXTERNAL_SERVICE_CONFIG_TYPE_MAP.get(adapter_type)
        if not config_class:
            raise ExternalServiceConfigurationError(
                f"Error creating External Service configuration. Type '{adapter_type}'"
            )

        config_instance = config_class.from_dict(data)
        if not isinstance(config_instance, ExternalServiceConfig):
            raise ExternalServiceConfigurationError(
                f"Deserialized config is not of type ExternalServiceConfig for adapter '{adapter_type}'"
            )
        return config_instance

    def _row_to_external_service(self, row: sqlite3.Row) -> Optional[ExternalService]:
        """Deserialize a row from the database into a ExternalService object."""
        if not row:
            return None
        try:
            adapter_type = ExternalServiceAdapter(row["adapter_type"])

            # Deserialize the config from the database row
            config = self._deserialize_config(adapter_type, row["config"])

            return ExternalService(
                id=EntityId(row["id"]),
                name=row["name"],
                adapter_type=adapter_type,
                config=config,
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing ExternalService from DB row: {row}. Error: {e}")
            return None

    def add(self, external_service: ExternalService) -> None:
        """Add a new external service to the repository."""
        self.logger.debug(f"Adding external service {external_service.id} to SQLite repository.")
        sql = """
            INSERT INTO external_services (id, name, adapter_type, config)
            VALUES (?, ?, ?, ?);
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json: str = ""
            if external_service.config:
                config_json = json.dumps(external_service.config.to_dict())

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        external_service.id,
                        external_service.name,
                        external_service.adapter_type.value,
                        config_json,
                    ),
                )
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding external service {external_service.id}: {e}")
            # Could mean that the ID already exists
            raise ExternalServiceAlreadyExistsError(
                f"external service with ID {external_service.id} already exists or constraint violation: {e}"
            ) from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding external service {external_service.id}: {e}")
            raise ExternalServiceError(f"DB error adding external service: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, external_service_id: EntityId) -> Optional[ExternalService]:
        """Retrieve a external service by its ID."""
        self.logger.debug(f"Retrieving external service {external_service_id} from SQLite repository.")
        sql = "SELECT * FROM external_services WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (external_service_id,))
            row = cursor.fetchone()
            return self._row_to_external_service(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving external service {external_service_id}: {e}")
            raise ExternalServiceNotFoundError(f"DB error retrieving external service: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[ExternalService]:
        """Retrieve all external services from the repository."""
        self.logger.debug("Retrieving all external services from SQLite repository.")
        sql = "SELECT * FROM external_services;"
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            external_services = []
            for row in rows:
                external_service = self._row_to_external_service(row)
                if external_service:
                    external_services.append(external_service)
            return external_services
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error retrieving all external services: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update(self, external_service: ExternalService) -> None:
        """Update an existing external service in the repository."""
        self.logger.debug(f"Updating external service {external_service.id} in SQLite repository.")
        sql = """
            UPDATE external_services
            SET name = ?, adapter_type = ?, config = ?
            WHERE id = ?;
        """
        conn = self._db.get_connection()
        try:
            # Serialize config to JSON for storage
            config_json = json.dumps(external_service.config)

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        external_service.name,
                        external_service.adapter_type.value,
                        config_json,
                        external_service.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ExternalServiceNotFoundError(f"External service with ID {external_service.id} not found.")
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating external service {external_service.id}: {e}")
            raise ExternalServiceError(f"DB error updating external service: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, external_service_id: EntityId) -> None:
        """Remove a external service from the repository."""
        self.logger.debug(f"Removing external service {external_service_id} from SQLite repository.")
        sql = "DELETE FROM external_services WHERE id = ?;"
        conn = self._db.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (external_service_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(f"Attempted to remove non-existent external service {external_service_id}.")
                    # There is no need to raise an exception here, removing a
                    # non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing external service {external_service_id}: {e}")
            raise ExternalServiceError(f"DB error removing external service: {e}") from e
        finally:
            if conn:
                conn.close()
