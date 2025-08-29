"""
pyasic adapter (Implementation of Port)
that controls a miner via pyasic.
"""
import asyncio
from typing import Dict, Optional

import pyasic

from edge_mining.domain.common import Watts
from edge_mining.domain.miner.common import MinerStatus
from edge_mining.domain.miner.entities import Miner
from edge_mining.domain.miner.exceptions import MinerControllerConfigurationError
from edge_mining.domain.miner.ports import MinerControlPort
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.shared.adapter_configs.miner import MinerControllerPyASICConfig
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.config import Configuration
from edge_mining.shared.interfaces.factories import MinerControllerAdapterFactory
from edge_mining.shared.logging.port import LoggerPort


class PyASICMinerControllerAdapterFactory(MinerControllerAdapterFactory):
    """
    Create a factory for pyasic Miner Controller Adapter.
    This factory is used to create instances of the adapter.
    """

    def __init__(self):
        self._miner: Optional[Miner] = None

    def from_miner(self, miner: Miner):
        """Set the miner for this controller."""
        self._miner = miner

    def create(
        self,
        config: Optional[Configuration] = None,
        logger: Optional[LoggerPort] = None,
        external_service: Optional[ExternalServicePort] = None,
    ) -> MinerControlPort:
        """Create a miner controller adapter instance."""

        if not isinstance(config, MinerControllerPyASICConfig):
            raise MinerControllerConfigurationError(
                "Invalid configuration for pyasic Miner Controller."
            )

        # Get the config from the provided configuration
        miner_controller_configuration: MinerControllerPyASICConfig = config

        return PyASICMinerController(
            ip=miner_controller_configuration.ip,
            logger=logger,
        )


class PyASICMinerController(MinerControlPort):
    """Controls a miner via pyasic."""

    def __init__(
        self,
        ip: str,
        logger: Optional[LoggerPort] = None,
    ):
        self.logger = logger

        self.ip = ip

        self._miner = None

        self._log_configuration()

    def _log_configuration(self):
        if self.logger:
            self.logger.debug(
                f"Entities Configured: IP={self.ip}"
            )

    def _get_miner(self) -> Optional[pyasic.AnyMiner]:
        if self._miner is None:
            self._miner = asyncio.run(pyasic.get_miner(self.ip))
        return self._miner


    def get_miner_hashrate(self) -> Optional[HashRate]:
        """
        Gets the current hash rate, if available.
        """

        if self.logger:
            self.logger.debug(f"Fetching hashrate from from {self.ip}...")

        hashrate = asyncio.run(self._get_miner().get_hashrate())
        if hashrate is None:
            if self.logger:
                self.logger.debug(f"Failed to fetch hashrate from {self.ip}...")
            return None
        real_hashrate =  HashRate(
            value=float(hashrate),
            unit=str(hashrate.unit)
        )

        if self.logger:
            self.logger.debug(f"Hashrate fetched: {real_hashrate}")

        return real_hashrate

    def get_miner_power(self) -> Optional[Watts]:
        """Gets the current power consumption, if available."""
        if self.logger:
            self.logger.debug(f"Fetching power consumption from from {self.ip}...")

        wattage = asyncio.run(self._get_miner().get_wattage())
        if wattage is None:
            if self.logger:
                self.logger.debug(f"Failed to fetch power consumption from {self.ip}...")
            return None
        power_watts =  Watts(wattage)

        if self.logger:
            self.logger.debug(f"Power consumption fetched: {power_watts}")

        return power_watts

    def get_miner_status(self) -> MinerStatus:
        """Gets the current operational status of the miner."""
        if self.logger:
            self.logger.debug(f"Fetching miner status from {self.ip}...")

        mining_state = asyncio.run(self._get_miner().is_mining())

        state_map: Dict[Optional[bool], MinerStatus] = {
            True: MinerStatus.ON,
            False: MinerStatus.OFF,
            None: MinerStatus.UNKNOWN,
        }

        miner_status = state_map.get(mining_state, MinerStatus.UNKNOWN)

        if self.logger:
            self.logger.debug(f"Miner status fetched: {miner_status}")

        return miner_status

    def stop_miner(self) -> bool:
        """Attempts to stop the specified miner. Returns True on success request."""
        if self.logger:
            self.logger.debug(f"Sending stop command to miner at {self.ip}...")

        success = asyncio.run(self._get_miner().stop_mining())

        if self.logger:
            self.logger.debug(f"Stop command sent. Success: {success}")

        return success

    def start_miner(self) -> bool:
        """Attempts to start the miner. Returns True on success request."""
        if self.logger:
            self.logger.debug(f"Sending start command to miner at {self.ip}...")

        success = asyncio.run(self._get_miner().resume_mining())

        if self.logger:
            self.logger.debug(f"Start command sent. Success: {success}")

        return success
