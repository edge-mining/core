import copy
import sqlite3
import uuid
import json
from typing import Optional, Dict, Any

from edge_mining.domain.exceptions import ConfigurationError

from edge_mining.domain.home_load.aggregate_roots import HomeLoadsProfile
from edge_mining.domain.home_load.ports import HomeLoadsProfileRepository
from edge_mining.domain.home_load.entities import LoadDevice

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository

# Simple In-Memory implementation for testing and basic use

class InMemoryHomeLoadsProfileRepository(HomeLoadsProfileRepository):
    def __init__(self, initial_profile: Optional[HomeLoadsProfile] = None):
        self._profile: Optional[HomeLoadsProfile] = copy.deepcopy(initial_profile)

    def get_profile(self) -> Optional[HomeLoadsProfile]:
        return copy.deepcopy(self._profile)

    def save_profile(self, profile: HomeLoadsProfile) -> None:
        self._profile = copy.deepcopy(profile)

class SqliteHomeLoadsProfileRepository(BaseSqliteRepository, HomeLoadsProfileRepository):
    _DEFAULT_PROFILE_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001") # UUID fisso per il profilo

    def _device_to_dict(self, device: LoadDevice) -> Dict[str, Any]:
        return {
            'id': str(device.id),
            'name': device.name,
            'type': device.type
        }

    def _dict_to_device(self, data: Dict[str, Any]) -> LoadDevice:
         return LoadDevice(
             id=uuid.UUID(data['id']),
             name=data['name'],
             type=data['type']
         )

    def _row_to_profile(self, row: sqlite3.Row) -> Optional[HomeLoadsProfile]:
        if not row:
            return None
        try:
            devices_data: Dict = json.loads(row["devices_json"] or '{}')
            devices = {
                uuid.UUID(id_str): self._dict_to_device(dev_dict)
                for id_str, dev_dict in devices_data.items()
            }
            return HomeLoadsProfile(
                id=row["id"], # UUID
                name=row["name"],
                devices=devices
            )
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error deserializing HomeLoadsProfile from DB line: {dict(row)}. Error: {e}")
            return None


    def get_profile(self) -> Optional[HomeLoadsProfile]:
        self.logger.debug("Getting home load profile from SQLite.")
        sql = "SELECT * FROM home_profiles WHERE id = ?"
        conn = self._get_connection()
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
            if conn: conn.close()

    def save_profile(self, profile: HomeLoadsProfile) -> None:
        self.logger.debug(f"Saving home load profile '{profile.name}' to SQLite.")
        sql = "INSERT OR REPLACE INTO home_profiles (id, name, devices_json) VALUES (?, ?, ?)"
        conn = self._get_connection()
        try:
            # Serialize the dictionary of devices
            devices_json = json.dumps({
                str(id): self._device_to_dict(dev)
                for id, dev in profile.devices.items()
            })
            with conn:
                # Usa sempre l'UUID fisso per salvare/sovrascrivere il profilo di default
                conn.execute(sql, (self._DEFAULT_PROFILE_UUID, profile.name, devices_json))
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error saving home profile: {e}")
            raise ConfigurationError(f"DB error saving home profile: {e}") from e
        finally:
            if conn: conn.close()