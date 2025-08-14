import copy
import sqlite3
import uuid
import json
from typing import List, Optional, Dict, Any

from edge_mining.domain.common import Watts
from edge_mining.domain.exceptions import MinerError

from edge_mining.domain.miner.common import MinerId, MinerStatus
from edge_mining.domain.miner.entities import Miner
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.miner.ports import MinerRepository

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository

# Simple In-Memory implementation for testing and basic use

class InMemoryMinerRepository(MinerRepository):
    """In-Memory implementation for the Miner Repository."""
    def __init__(self, initial_miners: Optional[Dict[MinerId, Miner]] = None):
        self._miners: Dict[MinerId, Miner] = copy.deepcopy(initial_miners) if initial_miners else {}

    def generate_id(self) -> MinerId:
        """Generates a new unique ID for a miner."""
        return MinerId(str(uuid.uuid4()))

    def add(self, miner: Miner) -> None:
        """Add a miner to the In-Memory repository."""
        if miner.id in self._miners:
            # Handle update or raise error depending on desired behavior
            print(f"Warning: Miner {miner.id} already exists, overwriting.")
        self._miners[miner.id] = copy.deepcopy(miner)

    def get_by_id(self, miner_id: MinerId) -> Optional[Miner]:
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

    def remove(self, miner_id: MinerId) -> None:
        """Remove a miner from the In-Memory repository."""
        if miner_id in self._miners:
            del self._miners[miner_id]

class SqliteMinerRepository(BaseSqliteRepository, MinerRepository):
    """SQLite implementation for the Miner Repository."""
    def generate_id(self) -> MinerId:
        """Generates a new unique ID for a miner."""
        return MinerId(str(uuid.uuid4()))

    def _dict_to_hashrate(self, data: Dict[str, Any]) -> HashRate:
        """Deserialize a dictionary (from JSON) into an HashRate object."""
        return HashRate(
            value=float(data['value']),
            unit=data['unit']
        )

    def _hashrate_to_dict(self, hash_rate: HashRate) -> Dict[str, Any]:
        """Serializes an HashRate object into a dictionary for JSON."""
        return {
            'value': hash_rate.value,
            'unit': hash_rate.unit
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
                id=MinerId(row["id"]),
                name=row["name"] if row["name"] is not None else "",
                ip_address=row["ip_address"] if row["ip_address"] is not None else "",
                status=MinerStatus(row["status"]),
                active=row["active"] == 1 if row["active"] is not None else False,
                hash_rate=hash_rate,
                hash_rate_max=hash_rate_max,
                power_consumption=Watts(row["power_consumption"]) if row["power_consumption"] is not None else None,
                power_consumption_max=Watts(row["power_consumption_max"]) if row["power_consumption_max"] is not None else None
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error deserializing Miner from DB row: {row}. Errorr: {e}")
            return None

    def add(self, miner: Miner) -> None:
        """Add a miner to the SQLite database."""
        self.logger.debug(f"Adding miner {miner.id} to SQLite.")

        sql = """
            INSERT INTO miners (id, name, ip_address, status, active, hash_rate, hash_rate_max power_consumption, power_consumption_max)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._get_connection()
        try:
            # Serialize hash_rate to JSON for storage
            hash_rate_json = json.dumps(self._hashrate_to_dict(miner.hash_rate))
            hash_rate_max_json = json.dumps(self._hashrate_to_dict(miner.hash_rate_max))

            with conn:
                conn.execute(sql, (
                    miner.id,
                    miner.name,
                    miner.ip_address,
                    miner.status.value,
                    miner.active,
                    hash_rate_json,
                    hash_rate_max_json,
                    float(miner.power_consumption) if miner.power_consumption is not None else None,
                    float(miner.power_consumption_max) if miner.power_consumption_max is not None else None
                ))
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding miner {miner.id}: {e}")
            # Potrebbe significare che l'ID esiste già
            raise MinerError(f"Miner with ID {miner.id} already exists or constraint violation: {e}") from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding miner {miner.id}: {e}")
            raise MinerError(f"DB error adding miner: {e}") from e
        finally:
            if conn: conn.close()

    def get_by_id(self, miner_id: MinerId) -> Optional[Miner]:
        """Get a miner by ID from the SQLite database."""
        self.logger.debug(f"Getting miner {miner_id} from SQLite.")

        sql = "SELECT * FROM miners WHERE id = ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (miner_id,))
            row = cursor.fetchone()
            return self._row_to_miner(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting miner {miner_id}: {e}")
            return None # Or raise exception? Returning None is more forgiving
        finally:
            if conn: conn.close()

    def get_all(self) -> List[Miner]:
        """Get all miners from the SQLite database."""
        self.logger.debug("Getting all miners from SQLite.")

        sql = "SELECT * FROM miners"
        conn = self._get_connection()
        miners = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                miner = self._row_to_miner(row)
                if miner:
                    miners.append(miner)
            return miners
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all miners: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update(self, miner: Miner) -> None:
        """Update a miner in the SQLite database."""
        self.logger.debug(f"Updating miner {miner.id} in SQLite.")

        sql = """
            UPDATE miners
            SET name = ?, ip_address = ?, status = ?, active = ?, hash_rate = ?, hash_rate_max = ? power_consumption = ?, power_consumption_max = ?
            WHERE id = ?
        """
        conn = self._get_connection()
        try:
            # Serialize hash_rate to JSON for storage
            hash_rate_json = json.dumps(self._hashrate_to_dict(miner.hash_rate))
            hash_rate_max_json = json.dumps(self._hashrate_to_dict(miner.hash_rate_max))
            
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    miner.name,
                    miner.ip_address,
                    miner.status.value,
                    miner.active,
                    hash_rate_json,
                    hash_rate_max_json,
                    float(miner.power_consumption) if miner.power_consumption is not None else None,
                    float(miner.power_consumption_max) if miner.power_consumption_max is not None else None,
                    miner.id
                ))
                if cursor.rowcount == 0:
                    raise MinerError(f"No miner found with ID {miner.id} for update.")
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating miner {miner.id}: {e}")
            raise MinerError(f"DB error updating miner: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, miner_id: MinerId) -> None:
        """Remove a miner from the SQLite database."""
        self.logger.debug(f"Removing miner {miner_id} from SQLite.")

        sql = "DELETE FROM miners WHERE id = ?"
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (miner_id,))
                if cursor.rowcount == 0:
                    self.logger.warning(f"Attempt to remove non-existent miner with ID {miner_id}.")
                    # There is no need to raise an exception here, removing a non-existent is idempotent.
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing miner {miner_id}: {e}")
            raise MinerError(f"DB error removing miner: {e}") from e
        finally:
            if conn:
                conn.close()
