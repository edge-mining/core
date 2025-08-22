"""Unit tests for EnergySource entity."""

import uuid

from edge_mining.domain.common import EntityId, WattHours, Watts
from edge_mining.domain.energy.common import EnergySourceType
from edge_mining.domain.energy.entities import EnergySource
from edge_mining.domain.energy.value_objects import Battery, Grid


class TestEnergySource:
    """Test suite for EnergySource entity."""

    def test_energy_source_creation_with_defaults(self):
        """Test creating an EnergySource with default values."""
        energy_source = EnergySource()

        assert energy_source.name == ""
        assert energy_source.type == EnergySourceType.SOLAR
        assert energy_source.nominal_power_max is None
        assert energy_source.storage is None
        assert energy_source.grid is None
        assert energy_source.external_source is None
        assert energy_source.energy_monitor_id is None
        assert energy_source.forecast_provider_id is None
        assert isinstance(energy_source.id, uuid.UUID)

    def test_energy_source_creation_with_custom_values(self):
        """Test creating an EnergySource with custom values."""
        custom_id = EntityId(uuid.uuid4())
        battery = Battery(nominal_capacity=WattHours(15000))
        grid = Grid(contracted_power=Watts(3000))

        energy_source = EnergySource(
            id=custom_id,
            name="Solar Panel Array",
            type=EnergySourceType.SOLAR,
            nominal_power_max=Watts(5000),
            storage=battery,
            grid=grid,
            external_source=Watts(1000),
        )

        assert energy_source.id == custom_id
        assert energy_source.name == "Solar Panel Array"
        assert energy_source.type == EnergySourceType.SOLAR
        assert energy_source.nominal_power_max == Watts(5000)
        assert energy_source.storage == battery
        assert energy_source.grid == grid
        assert energy_source.external_source == Watts(1000)

    def test_connect_to_grid(self):
        """Test connecting energy source to grid."""
        energy_source = EnergySource()
        grid = Grid(contracted_power=Watts(3000))

        energy_source.connect_to_grid(grid)

        assert energy_source.grid == grid

    def test_disconnect_from_grid(self):
        """Test disconnecting energy source from grid."""
        energy_source = EnergySource()
        grid = Grid(contracted_power=Watts(3000))
        energy_source.connect_to_grid(grid)

        energy_source.disconnect_from_grid()

        assert energy_source.grid is None

    def test_connect_to_external_source(self):
        """Test connecting to external power source."""
        energy_source = EnergySource()
        external_power = Watts(2500)

        energy_source.connect_to_external_source(external_power)

        assert energy_source.external_source == external_power

    def test_disconnect_from_external_source(self):
        """Test disconnecting from external power source."""
        energy_source = EnergySource()
        energy_source.connect_to_external_source(Watts(2500))

        energy_source.disconnect_from_external_source()

        assert energy_source.external_source is None

    def test_connect_to_storage(self):
        """Test connecting energy source to battery storage."""
        energy_source = EnergySource()
        battery = Battery(nominal_capacity=WattHours(15000))

        energy_source.connect_to_storage(battery)

        assert energy_source.storage == battery

    def test_disconnect_from_storage(self):
        """Test disconnecting energy source from battery storage."""
        energy_source = EnergySource()
        battery = Battery(nominal_capacity=WattHours(15000))
        energy_source.connect_to_storage(battery)

        energy_source.disconnect_from_storage()

        assert energy_source.storage is None

    def test_use_energy_monitor(self):
        """Test setting energy monitor for the energy source."""
        energy_source = EnergySource()
        monitor_id = EntityId(uuid.uuid4())

        energy_source.use_energy_monitor(monitor_id)

        assert energy_source.energy_monitor_id == monitor_id

    def test_use_forecast_provider(self):
        """Test setting forecast provider for the energy source."""
        energy_source = EnergySource()
        forecast_id = EntityId(uuid.uuid4())

        energy_source.use_forecast_provider(forecast_id)

        assert energy_source.forecast_provider_id == forecast_id

    def test_energy_source_type_variations(self):
        """Test creating energy sources with different types."""
        wind_source = EnergySource(name="Wind Turbine", type=EnergySourceType.WIND)
        hydro_source = EnergySource(name="Hydro Plant", type=EnergySourceType.HYDROELECTRIC)
        solar_source = EnergySource(name="Solar Plant", type=EnergySourceType.SOLAR)

        assert wind_source.type == EnergySourceType.WIND
        assert hydro_source.type == EnergySourceType.HYDROELECTRIC
        assert solar_source.type == EnergySourceType.SOLAR

    def test_complete_configuration_workflow(self):
        """Test a complete configuration workflow for an energy source."""
        # Create energy source
        energy_source = EnergySource(
            name="Complete Solar System",
            type=EnergySourceType.SOLAR,
            nominal_power_max=Watts(8000),
        )

        # Add storage
        battery = Battery(nominal_capacity=WattHours(15000))
        energy_source.connect_to_storage(battery)

        # Connect to grid
        grid = Grid(contracted_power=Watts(3000))
        energy_source.connect_to_grid(grid)

        # Add external backup
        energy_source.connect_to_external_source(Watts(3000))

        # Configure monitoring
        monitor_id = EntityId(uuid.uuid4())
        forecast_id = EntityId(uuid.uuid4())
        energy_source.use_energy_monitor(monitor_id)
        energy_source.use_forecast_provider(forecast_id)

        # Verify complete configuration
        assert energy_source.name == "Complete Solar System"
        assert energy_source.type == EnergySourceType.SOLAR
        assert energy_source.nominal_power_max == Watts(8000)
        assert energy_source.storage == battery
        assert energy_source.grid == grid
        assert energy_source.external_source == Watts(3000)
        assert energy_source.energy_monitor_id == monitor_id
        assert energy_source.forecast_provider_id == forecast_id

    def test_partial_disconnection_workflow(self):
        """Test disconnecting only some components."""
        energy_source = EnergySource(name="Test Source")

        # Setup all connections
        battery = Battery(nominal_capacity=WattHours(15000))
        grid = Grid(contracted_power=Watts(3000))
        external_source = Watts(1500)
        energy_source.connect_to_storage(battery)
        energy_source.connect_to_grid(grid)
        energy_source.connect_to_external_source(external_source)

        # Disconnect only storage
        energy_source.disconnect_from_storage()

        # Verify only storage is disconnected
        assert energy_source.storage is None
        assert energy_source.grid == grid
        assert energy_source.external_source == external_source

    def test_multiple_reconnections(self):
        """Test reconnecting components multiple times."""
        energy_source = EnergySource()

        # First connection
        first_battery = Battery(nominal_capacity=WattHours(5000))
        energy_source.connect_to_storage(first_battery)
        assert energy_source.storage == first_battery

        # Reconnect with different battery
        second_battery = Battery(nominal_capacity=WattHours(8000))
        energy_source.connect_to_storage(second_battery)
        assert energy_source.storage == second_battery
        assert energy_source.storage != first_battery

    def test_energy_source_identity_persistence(self):
        """Test that entity identity is maintained through operations."""
        energy_source = EnergySource(name="Test Source")
        original_id = energy_source.id

        # Perform various operations
        battery = Battery(nominal_capacity=WattHours(5000))
        energy_source.connect_to_storage(battery)
        energy_source.disconnect_from_storage()
        energy_source.use_energy_monitor(EntityId(uuid.uuid4()))

        # Verify ID hasn't changed
        assert energy_source.id == original_id


class TestEnergySourceWithFixtures:
    """Additional tests using fixtures."""

    def test_energy_source_with_fixtures(self, sample_energy_source, sample_battery, sample_grid):
        """Test energy source operations using fixtures."""
        # Use fixtures
        sample_energy_source.connect_to_storage(sample_battery)
        sample_energy_source.connect_to_grid(sample_grid)

        assert sample_energy_source.storage == sample_battery
        assert sample_energy_source.grid == sample_grid
        assert sample_energy_source.name == "Test Solar Panel"

    def test_fixture_isolation(self, sample_energy_source):
        """Test that fixtures are isolated between tests."""
        # This should start fresh even though previous test modified the fixture
        assert sample_energy_source.storage is None
        assert sample_energy_source.grid is None
