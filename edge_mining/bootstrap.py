"""Bootstrap operations"""
import os

from edge_mining.domain.energy.ports import EnergyMonitorPort
from edge_mining.domain.miner.common import MinerId, MinerStatus
from edge_mining.domain.miner.ports import MinerControlPort, MinerRepository
from edge_mining.domain.forecast.ports import ForecastProviderPort
from edge_mining.domain.home_load.ports import HomeForecastProviderPort, HomeLoadsProfileRepository
from edge_mining.domain.notification.ports import NotificationPort
from edge_mining.domain.performance.ports import MiningPerformanceTrackerPort
from edge_mining.domain.policy.ports import OptimizationPolicyRepository
from edge_mining.domain.user.ports import SettingsRepository

from edge_mining.shared.settings.common import (
    PersistenceAdapter, EnergyMonitorAdapter, MinerControllerAdapter, ForecastProviderAdapter,
    HomeForecastProviderAdapter, NotificationAdapter, PerformaceTrackerAdapter, ExternalServiceAdapter
)

from edge_mining.adapters.domain.energy_monitoring.dummy import DummyEnergyMonitor
from edge_mining.adapters.domain.miner.dummy import DummyMinerController
from edge_mining.adapters.domain.forecast.dummy import DummyForecastProvider
from edge_mining.adapters.domain.home_load.dummy import DummyHomeForecastProvider
from edge_mining.adapters.domain.notification.dummy import DummyNotifier
from edge_mining.adapters.domain.performance.dummy import DummyPerformanceTracker

from edge_mining.adapters.infrastructure.homeassistant.homeassistant_api import ServiceHomeAssistantAPI

from edge_mining.adapters.domain.energy_monitoring.home_assistant_api import HomeAssistantEnergyMonitor
from edge_mining.adapters.domain.forecast.home_assistant_api import HomeAssistantForecastProvider
from edge_mining.adapters.domain.notification.telegram import TelegramNotifier

from edge_mining.adapters.domain.miner.repositories import InMemoryMinerRepository, SqliteMinerRepository
from edge_mining.adapters.domain.policy.repositories import InMemoryOptimizationPolicyRepository, SqliteOptimizationPolicyRepository
from edge_mining.adapters.domain.home_load.repositories import InMemoryHomeLoadsProfileRepository, SqliteHomeLoadsProfileRepository
from edge_mining.adapters.domain.user.repositories import InMemorySettingsRepository, SqliteSettingsRepository

from edge_mining.shared.logging.port import LoggerPort
from edge_mining.shared.settings.settings import AppSettings

from edge_mining.application.services.configuration_service import ConfigurationService
from edge_mining.application.services.mining_orchestrator import MiningOrchestratorService

def configure_dependencies(logger: LoggerPort, settings: AppSettings):
    """
    Performs Dependency Injection - Creates instances of adapters and services.
    Returns the main application services.
    """

    logger.debug("Configuring dependencies...")

    # --- Persistence ---
    if PersistenceAdapter(settings.persistence_adapter) == PersistenceAdapter.IN_MEMORY:
        # Pre-populate in-memory repos with some test data (used for debug or development)
        miner_repo: MinerRepository = InMemoryMinerRepository()
        policy_repo: OptimizationPolicyRepository = InMemoryOptimizationPolicyRepository()
        settings_repo: SettingsRepository = InMemorySettingsRepository()
        home_profile_repo: HomeLoadsProfileRepository = InMemoryHomeLoadsProfileRepository()

        logger.debug("Using InMemory persistence adapters.")
    elif PersistenceAdapter(settings.persistence_adapter) == PersistenceAdapter.SQLITE:
        db_path = settings.sqlite_db_file
        
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            logger.debug(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)

        logger.debug(f"Using SQLite persistence adapter (DB: {db_path}).")
        
        # Instantiate all SQLite repositories passing the DB path
        miner_repo: MinerRepository = SqliteMinerRepository(db_path=db_path, logger=logger)
        policy_repo: OptimizationPolicyRepository = SqliteOptimizationPolicyRepository(db_path=db_path, logger=logger)
        settings_repo: SettingsRepository = SqliteSettingsRepository(db_path=db_path, logger=logger)
        home_profile_repo: HomeLoadsProfileRepository = SqliteHomeLoadsProfileRepository(db_path=db_path, logger=logger)
        # user_repo: UserRepository = SqliteUserRepository(db_path=db_path, logger=logger) # If implemented
    else:
        raise ValueError(f"Unsupported persistence_adapter: {settings.persistence_adapter}")
    
    # --- External Services ---
    if ExternalServiceAdapter.HOME_ASSISTANT in [ExternalServiceAdapter(settings.energy_monitor_adapter), ExternalServiceAdapter(settings.forecast_provider_adapter)]:
        # Initialize Home Assistant API service
        try:
            home_assistant_api = ServiceHomeAssistantAPI(
                api_url=settings.home_assistant_url,
                token=settings.home_assistant_token,
                logger=logger
            )
        except (ValueError, ConnectionError, ImportError) as e:
            logger.error(f"Failed to initialize Home Assistant API: {e}")
            raise
    
    
    # --- Energy Monitor ---
    if EnergyMonitorAdapter(settings.energy_monitor_adapter) == EnergyMonitorAdapter.DUMMY:
        energy_monitor: EnergyMonitorPort = DummyEnergyMonitor(
            has_battery=settings.dummy_battery_present,
            battery_capacity_wh=settings.dummy_battery_capacity_wh
        )

        logger.debug("Using Dummy Energy Monitor adapter.")
    elif EnergyMonitorAdapter(settings.energy_monitor_adapter) == EnergyMonitorAdapter.HOME_ASSISTANT:
        try:
            energy_monitor: EnergyMonitorPort = HomeAssistantEnergyMonitor(
                home_assistant=home_assistant_api,
                entity_solar=settings.ha_entity_solar_production,
                entity_consumption=settings.ha_entity_house_consumption,
                entity_grid=settings.ha_entity_grid_power,
                entity_battery_soc=settings.ha_entity_battery_soc,
                entity_battery_power=settings.ha_entity_battery_power,
                unit_solar=settings.ha_unit_solar_production,
                unit_consumption=settings.ha_unit_house_consumption,
                unit_grid=settings.ha_unit_grid_power,
                unit_battery_power=settings.ha_unit_battery_power,
                battery_capacity_wh=settings.ha_battery_nominal_capacity_wh,
                grid_positive_export=settings.ha_grid_positive_export,
                battery_positive_charge=settings.ha_battery_positive_charge,
                logger=logger
            )

            logger.debug("Using Home Assistant Energy Monitor Adapter.")
        except (ValueError, ConnectionError, ImportError) as e:
            logger.error(f"Failed to initialize Home Assistant Energy Monitor Adapter: {e}")
            raise # Raise the exception to stop the execution
    else:
        raise ValueError(f"Unsupported energy_monitor_adapter: {settings.energy_monitor_adapter}")

    # --- Miner Controller ---
    if MinerControllerAdapter(settings.miner_controller_adapter) == MinerControllerAdapter.DUMMY:
        miner_controller: MinerControlPort = DummyMinerController(
            initial_status={
                MinerId("001"): MinerStatus.OFF,
                MinerId("002"): MinerStatus.ON
            },
            power_w=settings.dummy_miner_power_w
        )

        logger.debug("Using Dummy Miner Controller adapter.")
    else:
         raise ValueError(f"Unsupported miner_controller_adapter: {settings.miner_controller_adapter}")

    # --- Forecast Provider ---
    if ForecastProviderAdapter(settings.forecast_provider_adapter) == ForecastProviderAdapter.DUMMY:
        forecast_provider: ForecastProviderPort = DummyForecastProvider(
            latitude=settings.latitude,
            longitude=settings.longitude,
            capacity_kwp=settings.pv_capacity_kwp
        )

        logger.debug("Using Dummy Forecast Provider Adapter.")
    elif ForecastProviderAdapter(settings.forecast_provider_adapter) == ForecastProviderAdapter.HOME_ASSISTANT:
        try:
            forecast_provider: ForecastProviderPort = HomeAssistantForecastProvider(
                home_assistant=home_assistant_api,
                entity_solar_forecast_power_actual_h=settings.ha_entity_solar_forecast_power_actual_h,
                entity_solar_forecast_power_next_1h=settings.ha_entity_solar_forecast_power_next_1h,
                entity_solar_forecast_power_next_12h=settings.ha_entity_solar_forecast_power_next_12h,
                entity_solar_forecast_power_next_24h=settings.ha_entity_solar_forecast_power_next_24h,
                entity_solar_forecast_energy_actual_h=settings.ha_entity_solar_forecast_energy_actual_h,
                entity_solar_forecast_energy_next_1h=settings.ha_entity_solar_forecast_energy_next_1h,
                entity_solar_forecast_energy_next_24h=settings.ha_entity_solar_forecast_energy_next_24h,
                entity_solar_forecast_energy_remaining_today=settings.ha_entity_solar_forecast_energy_remaining_today,
                unit_solar_forecast_power_actual_h=settings.ha_unit_solar_forecast_power_actual_h,
                unit_solar_forecast_power_next_1h=settings.ha_unit_solar_forecast_power_next_1h,
                unit_solar_forecast_power_next_12h=settings.ha_unit_solar_forecast_power_next_12h,
                unit_solar_forecast_power_next_24h=settings.ha_unit_solar_forecast_power_next_24h,
                unit_solar_forecast_energy_actual_h=settings.ha_unit_solar_forecast_energy_actual_h,
                unit_solar_forecast_energy_next_1h=settings.ha_unit_solar_forecast_energy_next_1h,
                unit_solar_forecast_energy_next_24h=settings.ha_unit_solar_forecast_energy_next_24h,
                unit_solar_forecast_energy_remaining_today=settings.ha_unit_solar_forecast_energy_remaining_today,
                logger=logger
            )

            logger.debug("Using Home Assistant Forecast Provider adapter.")
        except (ValueError, ConnectionError, ImportError) as e:
            logger.error(f"Failed to initialize Home Assistant Forecast Provider Adapter: {e}")
            raise # Raise the exception to stop the execution
    else:
        raise ValueError(f"Unsupported forecast_provider_adapter: {settings.forecast_provider_adapter}")

    # --- Home Forecast Provider ---
    if HomeForecastProviderAdapter(settings.home_forecast_adapter) == HomeForecastProviderAdapter.DUMMY:
        home_forecast_provider: HomeForecastProviderPort = DummyHomeForecastProvider()

        logger.debug("Using Dummy Home Forecast Provider adapter.")
    else:
        raise ValueError(f"Unsupported home_forecast_adapter: {settings.home_forecast_adapter}")

    # --- Notification ---
    if NotificationAdapter(settings.notification_adapter) == NotificationAdapter.DUMMY:
        notifier: NotificationPort = DummyNotifier()

        logger.debug("Using Dummy Notifier adapter.")
    elif NotificationAdapter(settings.notification_adapter) == NotificationAdapter.TELEGRAM:
        if settings.telegram_bot_token and settings.telegram_chat_id:
            try:
                notifier: NotificationPort = TelegramNotifier(
                    bot_token=settings.telegram_bot_token,
                    chat_id=settings.telegram_chat_id
                )

                logger.debug("Using Telegram Notifier adapter.")
            except (ValueError, ConnectionError, ImportError) as e:
                logger.error(f"Failed to initialize Telegram notifier: {e}. Falling back to no notifications.")
                # We don't need to raise error, the application can run without notifier
    else:
        # Allow no notifier
        notifier = None
        logger.debug("No notification adapter configured.")
        # raise ValueError(f"Unsupported notification_adapter: {settings.notification_adapter}")

    # --- Performance Tracker ---
    if PerformaceTrackerAdapter(settings.performance_tracker_adapter) == PerformaceTrackerAdapter.DUMMY:
        perf_tracker: MiningPerformanceTrackerPort = DummyPerformanceTracker()
        
        logger.debug("Using Dummy Performance Tracker adapter.")
    else:
        perf_tracker = None # Or raise error
        logger.debug("No performance tracker configured.")

    # Instantiate Application Services, injecting adapters (ports)
    logger.debug("Instantiating application services...")
    config_service = ConfigurationService(
        miner_repo=miner_repo,
        policy_repo=policy_repo,
        settings_repo=settings_repo,
        logger=logger
        # Add home_profile_repo if needed by config service
    )

    orchestrator_service = MiningOrchestratorService(
        energy_monitor=energy_monitor,
        miner_controller=miner_controller,
        forecast_provider=forecast_provider,
        home_forecast_provider=home_forecast_provider,
        policy_repo=policy_repo,
        miner_repo=miner_repo,
        notifier=notifier,
        logger=logger
    )

    logger.debug("Dependency configuration complete.")
    return config_service, orchestrator_service