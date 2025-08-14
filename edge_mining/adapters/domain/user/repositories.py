import copy
import json
import sqlite3
from typing import Optional, Dict

from edge_mining.domain.exceptions import ConfigurationError

from edge_mining.domain.user.common import UserId
from edge_mining.domain.user.entities import SystemSettings
from edge_mining.shared.settings.ports import SettingsRepository

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository

# Simple In-Memory implementation for testing and basic use

class InMemorySettingsRepository(SettingsRepository):
    """In-Memory implementation of the SettingsRepository."""
    _SETTINGS_ID = "global_settings" # We dont have different users, so we use a single ID.

    def __init__(self, initial_settings: Optional[Dict[UserId, SystemSettings]] = None):
        self._settings: Dict[UserId, SystemSettings] = copy.deepcopy(initial_settings) if initial_settings else {}

    def get_settings(self, user_id: Optional[UserId]) -> Optional[SystemSettings]:
        user_id = user_id or self._SETTINGS_ID
        if user_id in self._settings:
            return copy.deepcopy(self._settings[user_id])
        return None

    def save_settings(self, settings: SystemSettings, user_id: Optional[UserId]) -> None:
        user_id = user_id or self._SETTINGS_ID
        self._settings[user_id] = copy.deepcopy(settings)

class SqliteSettingsRepository(BaseSqliteRepository, SettingsRepository):
    """SQLite implementation of the SettingsRepository."""
    _SETTINGS_ID = "global_settings" # We dont have different users, so we use a single ID.

    def get_settings(self, user_id: Optional[UserId]) -> Optional[SystemSettings]:
        self.logger.debug("Getting settings from SQLite.")
        sql = "SELECT settings_json FROM settings WHERE id = ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id or self._SETTINGS_ID,))
            row = cursor.fetchone()
            if row:
                settings_dict = json.loads(row["settings_json"])
                return SystemSettings(id=user_id or self._SETTINGS_ID, settings=settings_dict)
            else:
                self.logger.info("No settings found in DB, returning None.")
                return None # No settings found in DB, return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.logger.error(f"Errore SQLite o JSON ottenendo settings: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def save_settings(self, settings: SystemSettings, user_id: Optional[UserId]) -> None:
        self.logger.debug("Saving settings to SQLite.")

        sql = "INSERT OR REPLACE INTO settings (id, settings_json) VALUES (?, ?)"
        conn = self._get_connection()
        try:
            settings_json = json.dumps(settings.settings) # Serialize the inner dictionary
            with conn:
                conn.execute(sql, (user_id or self._SETTINGS_ID, settings_json))
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error saving settings: {e}")
            raise ConfigurationError(f"SQLite error saving settings: {e}") from e
        finally:
            if conn:
                conn.close()
