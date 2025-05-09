import copy
import json
import sqlite3
from typing import Optional

from edge_mining.domain.exceptions import ConfigurationError

from edge_mining.domain.user.ports import SettingsRepository
from edge_mining.domain.user.entities import SystemSettings

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository

# Simple In-Memory implementation for testing and basic use

class InMemorySettingsRepository(SettingsRepository):
    def __init__(self, initial_settings: Optional[SystemSettings] = None):
        self._settings: Optional[SystemSettings] = copy.deepcopy(initial_settings)

    def get_settings(self) -> Optional[SystemSettings]:
         return copy.deepcopy(self._settings)

    def save_settings(self, settings: SystemSettings) -> None:
        self._settings = copy.deepcopy(settings)

class SqliteSettingsRepository(BaseSqliteRepository, SettingsRepository):
    _SETTINGS_ID = "global_settings" # We dont have different users, so we use a single ID.

    def get_settings(self) -> Optional[SystemSettings]:
        self.logger.debug("Getting settings from SQLite.")
        
        sql = "SELECT settings_json FROM settings WHERE id = ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (self._SETTINGS_ID,))
            row = cursor.fetchone()
            if row:
                settings_dict = json.loads(row["settings_json"])
                # Ricrea l'oggetto SystemSettings
                # SystemSettings non ha un ID nel modello, lo usiamo solo in DB
                return SystemSettings(settings=settings_dict)
            else:
                self.logger.info("No settings found in DB, returning None.")
                return None # Nessuna impostazione ancora salvata
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.logger.error(f"Errore SQLite o JSON ottenendo settings: {e}")
            return None
        finally:
            if conn: conn.close()

    def save_settings(self, settings: SystemSettings) -> None:
        self.logger.debug("Saving settings to SQLite.")
        
        sql = "INSERT OR REPLACE INTO settings (id, settings_json) VALUES (?, ?)"
        conn = self._get_connection()
        try:
            settings_json = json.dumps(settings.settings) # Serializza il dizionario interno
            with conn:
                conn.execute(sql, (self._SETTINGS_ID, settings_json))
        except sqlite3.Error as e:
            self.logger.error(f"Errore SQLite salvando settings: {e}")
            raise ConfigurationError(f"Errore DB salvando settings: {e}") from e
        finally:
            if conn: conn.close()