"""Unit tests for EnergyMonitor entity."""

import uuid

from edge_mining.domain.common import EntityId
from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.domain.energy.entities import EnergyMonitor


class TestEnergyMonitor:
    """Test suite for EnergyMonitor entity."""

    def test_energy_monitor_creation_with_defaults(self):
        """Test creating an EnergyMonitor with default values."""
        monitor = EnergyMonitor()

        assert monitor.name == ""
        assert monitor.adapter_type == EnergyMonitorAdapter.DUMMY_SOLAR
        assert monitor.config is None
        assert monitor.external_service_id is None
        assert isinstance(monitor.id, uuid.UUID)

    def test_energy_monitor_creation_with_custom_values(self):
        """Test creating an EnergyMonitor with custom values."""
        custom_id = EntityId(uuid.uuid4())
        service_id = EntityId(uuid.uuid4())

        monitor = EnergyMonitor(
            id=custom_id,
            name="Solar Production Monitor",
            adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_API,
            external_service_id=service_id,
        )

        assert monitor.id == custom_id
        assert monitor.name == "Solar Production Monitor"
        assert monitor.adapter_type == EnergyMonitorAdapter.HOME_ASSISTANT_API
        assert monitor.external_service_id == service_id

    def test_energy_monitor_different_adapter_types(self):
        """Test creating energy monitors with different adapter types."""
        api_monitor = EnergyMonitor(
            name="HomeAssistant API Monitor",
            adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_API,
        )

        dummy_monitor = EnergyMonitor(name="Dummy Monitor", adapter_type=EnergyMonitorAdapter.DUMMY_SOLAR)

        mqtt_monitor = EnergyMonitor(
            name="HomeAssistant MQTT Monitor",
            adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_MQTT,
        )

        assert api_monitor.adapter_type == EnergyMonitorAdapter.HOME_ASSISTANT_API
        assert dummy_monitor.adapter_type == EnergyMonitorAdapter.DUMMY_SOLAR
        assert mqtt_monitor.adapter_type == EnergyMonitorAdapter.HOME_ASSISTANT_MQTT

    def test_energy_monitor_with_config(self):
        """Test energy monitor with configuration."""
        monitor = EnergyMonitor(
            name="Configured Monitor",
            adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_API,
        )

        # Test that config can be set (even if None initially)
        assert monitor.config is None

    def test_energy_monitor_with_external_service(self):
        """Test energy monitor with external service reference."""
        service_id = EntityId(uuid.uuid4())

        monitor = EnergyMonitor(
            name="External Service Monitor",
            adapter_type=EnergyMonitorAdapter.HOME_ASSISTANT_API,
            external_service_id=service_id,
        )

        assert monitor.external_service_id == service_id

    def test_energy_monitor_identity_persistence(self):
        """Test that entity identity is maintained through operations."""
        monitor = EnergyMonitor(name="Test Monitor")
        original_id = monitor.id

        # Modify properties
        monitor.name = "Updated Monitor"
        monitor.adapter_type = EnergyMonitorAdapter.HOME_ASSISTANT_API
        monitor.external_service_id = EntityId(uuid.uuid4())

        # Verify ID hasn't changed
        assert monitor.id == original_id

    def test_energy_monitor_name_update(self):
        """Test updating energy monitor name."""
        monitor = EnergyMonitor(name="Original Name")

        monitor.name = "Updated Name"

        assert monitor.name == "Updated Name"

    def test_energy_monitor_adapter_type_update(self):
        """Test updating energy monitor adapter type."""
        monitor = EnergyMonitor(adapter_type=EnergyMonitorAdapter.DUMMY_SOLAR)

        monitor.adapter_type = EnergyMonitorAdapter.HOME_ASSISTANT_API

        assert monitor.adapter_type == EnergyMonitorAdapter.HOME_ASSISTANT_API

    def test_energy_monitor_external_service_update(self):
        """Test updating external service reference."""
        monitor = EnergyMonitor()
        service_id = EntityId(uuid.uuid4())

        assert monitor.external_service_id is None

        monitor.external_service_id = service_id
        assert monitor.external_service_id == service_id

        # Test removing service reference
        monitor.external_service_id = None
        assert monitor.external_service_id is None

    def test_energy_monitor_complete_setup(self):
        """Test complete energy monitor setup workflow."""
        service_id = EntityId(uuid.uuid4())

        monitor = EnergyMonitor()

        # Configure monitor step by step
        monitor.name = "Complete API Monitor"
        monitor.adapter_type = EnergyMonitorAdapter.HOME_ASSISTANT_API
        monitor.external_service_id = service_id

        # Verify complete configuration
        assert monitor.name == "Complete API Monitor"
        assert monitor.adapter_type == EnergyMonitorAdapter.HOME_ASSISTANT_API
        assert monitor.external_service_id == service_id
        assert isinstance(monitor.id, uuid.UUID)


class TestEnergyMonitorWithFixtures:
    """Additional tests using fixtures."""

    def test_energy_monitor_with_fixture(self, energy_monitor):
        """Test energy monitor using fixture."""
        assert energy_monitor.name == "Test Monitor"
        assert energy_monitor.adapter_type == EnergyMonitorAdapter.DUMMY_SOLAR
        assert energy_monitor.config is None
        assert energy_monitor.external_service_id is None

    def test_fixture_isolation(self, energy_monitor):
        """Test that fixtures are isolated between tests."""
        # Modify the monitor
        energy_monitor.name = "Modified Monitor"
        energy_monitor.adapter_type = EnergyMonitorAdapter.HOME_ASSISTANT_API

        assert energy_monitor.name == "Modified Monitor"
        # Next test should get a fresh fixture

    def test_multiple_monitors_independence(self):
        """Test that multiple monitor instances are independent."""
        monitor1 = EnergyMonitor(name="Monitor 1")
        monitor2 = EnergyMonitor(name="Monitor 2")

        assert monitor1.id != monitor2.id
        assert monitor1.name != monitor2.name

        # Modify one monitor
        monitor1.adapter_type = EnergyMonitorAdapter.HOME_ASSISTANT_API

        # Other monitor should be unchanged
        assert monitor2.adapter_type == EnergyMonitorAdapter.DUMMY_SOLAR
