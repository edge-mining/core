"""Shared fixtures for energy domain tests."""

import uuid

import pytest

from edge_mining.domain.common import EntityId, WattHours, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter, EnergySourceType
from edge_mining.domain.energy.entities import EnergyMonitor, EnergySource
from edge_mining.domain.energy.value_objects import Battery, Grid


@pytest.fixture
def energy_source_id():
    """Fixture providing a sample EntityId for energy sources."""
    return EntityId(uuid.uuid4())


@pytest.fixture
def solar_energy_source():
    """Fixture providing a solar energy source."""
    return EnergySource(
        name="Solar Panel System",
        type=EnergySourceType.SOLAR,
        nominal_power_max=Watts(6000),
    )


@pytest.fixture
def wind_energy_source():
    """Fixture providing a wind energy source."""
    return EnergySource(name="Wind Turbine", type=EnergySourceType.WIND, nominal_power_max=Watts(3000))


@pytest.fixture
def basic_battery():
    """Fixture providing a basic battery."""
    return Battery(nominal_capacity=WattHours(10000))


@pytest.fixture
def large_battery():
    """Fixture providing a large capacity battery."""
    return Battery(nominal_capacity=WattHours(40000))


@pytest.fixture
def standard_grid():
    """Fixture providing a standard grid connection."""
    return Grid(contracted_power=Watts(3000))


@pytest.fixture
def high_power_grid():
    """Fixture providing a high power grid connection."""
    return Grid(contracted_power=Watts(6000))


@pytest.fixture
def energy_monitor():
    """Fixture providing a dummy energy monitor."""
    return EnergyMonitor(name="Test Monitor", adapter_type=EnergyMonitorAdapter.DUMMY_SOLAR)


@pytest.fixture
def external_generator_power():
    """Fixture providing external generator power rating."""
    return Watts(5000)


@pytest.fixture
def complete_energy_system(solar_energy_source, basic_battery, standard_grid):
    """Fixture providing a complete energy system setup."""
    solar_energy_source.connect_to_storage(basic_battery)
    solar_energy_source.connect_to_grid(standard_grid)
    return solar_energy_source


@pytest.fixture
def sample_energy_source():
    """Fixture providing a sample energy source for tests."""
    return EnergySource(
        name="Test Solar Panel",
        type=EnergySourceType.SOLAR,
        nominal_power_max=Watts(5000),
    )


@pytest.fixture
def sample_battery():
    """Fixture providing a sample battery for tests."""
    return Battery(nominal_capacity=WattHours(10000))


@pytest.fixture
def sample_grid():
    """Fixture providing a sample grid for tests."""
    return Grid(contracted_power=Watts(3000))


# Additional fixtures specific to EnergyMonitor tests
@pytest.fixture
def home_assistant_api_monitor():
    """Fixture providing a Home Assistant API energy monitor."""
    return EnergyMonitor(
        name="Home Assistant API Monitor",
        adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_API,
    )


@pytest.fixture
def home_assistant_mqtt_monitor():
    """Fixture providing a Home Assistant MQTT energy monitor."""
    return EnergyMonitor(
        name="Home Assistant MQTT Monitor",
        adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_MQTT,
    )


@pytest.fixture
def dummy_monitor():
    """Fixture providing a dummy energy monitor."""
    return EnergyMonitor(name="Dummy Monitor", adapter_type=EnergyMonitorAdapter.DUMMY_SOLAR)


@pytest.fixture
def monitor_with_service():
    """Fixture providing a monitor with external service."""
    return EnergyMonitor(
        name="Service Monitor",
        adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_API,
        external_service_id=EntityId(uuid.uuid4()),
    )
