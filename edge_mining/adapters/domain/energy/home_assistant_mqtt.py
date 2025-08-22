import math
import ssl  # Per TLS
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple, Union

import paho.mqtt.client as mqtt

from edge_mining.domain.common import Percentage, Timestamp, WattHours, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.domain.energy.ports import EnergyMonitorPort
from edge_mining.domain.energy.value_objects import BatteryState, EnergyStateSnapshot, GridState, LoadState
from edge_mining.shared.logging.port import LoggerPort


class MqttEnergyMonitor(EnergyMonitorPort):
    """
    Fetches energy data by subscribing to topics on an MQTT broker.

    It maintains the latest received values internally and returns a snapshot
    when get_current_energy_state is called.
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        username: Optional[str],
        password: Optional[str],
        client_id: str,
        topics: Dict[str, Optional[str]],  # Map internal name to topic string
        units: Dict[str, str],
        conventions: Dict[str, bool],
        battery_capacity_wh: Optional[float],
        max_data_age_seconds: int,
        logger: Optional[LoggerPort] = None,
    ):
        super().__init__(energy_monitor_type=EnergyMonitorAdapter.HOME_ASSISTANT_MQTT)

        self.logger = logger

        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client_id = f"{client_id}-{int(time.time())}"
        self.topics_map = {k: v for k, v in topics.items() if v}
        self.units_map = units
        self.conventions = conventions
        self.battery_capacity = WattHours(battery_capacity_wh) if battery_capacity_wh else None
        self.max_data_age = timedelta(seconds=max_data_age_seconds)

        # Store latest value by internal sensor name
        self._latest_values: Dict[str, Any] = {}
        # Store last update timestamp by internal sensor name
        self._last_update_times: Dict[str, datetime] = {}
        # Lock for thread-safe access to latest values and timestamps
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._client: Optional[mqtt.Client] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        if self.logger:
            self.logger.info(f"Initializing MqttEnergyMonitor for {broker_host}:{broker_port}")
            self.logger.debug(f"Client ID: {self.client_id}")
            self.logger.debug(f"Topics configured: {self.topics_map}")
            self.logger.debug(f"Units: {self.units_map}")
            self.logger.debug(f"Conventions: {self.conventions}")
            if self.battery_capacity:
                self.logger.debug(f"Static Battery Capacity: {self.battery_capacity} Wh")
            self.logger.debug(f"Max data age: {self.max_data_age} seconds")

        if not self.topics_map:
            if self.logger:
                self.logger.warning("MQTT Energy Monitor initialized, but no topics were configured.")
            # The adapter will still run, but won't receive any data.

        self._setup_client()

    def _setup_client(self):
        """Configure the MQTT client and start the loop in a separate thread."""
        try:
            try:
                self._client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv5)
                if self.logger:
                    self.logger.debug("Using MQTTv5 protocol.")
            except ValueError:
                if self.logger:
                    self.logger.warning("MQTTv5 not supported by paho-mqtt version or broker? Falling back to v3.1.1.")
                self._client = mqtt.Client(client_id=self.client_id)  # Default (v3.1.1)

            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            self._client.on_log = self._on_log

            if self.username:
                self._client.username_pw_set(self.username, self.password)

            # TLS management (it is basic, add more options if needed)
            if self.broker_port == 8883:  # Porta standard per MQTTS
                if self.logger:
                    self.logger.info("Configuring TLS for MQTT connection (port 8883 detected).")
                # Use default system certs
                self._client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
                # For custom certs: self._client.tls_set(ca_certs="ca.crt",
                # certfile="client.crt", keyfile="client.key")

            if self.logger:
                self.logger.info(f"Connecting MQTT client to {self.broker_host}:{self.broker_port}...")
            self._client.connect_async(self.broker_host, self.broker_port, 60)

            # Run the MQTT loop in a separate thread to avoid blocking
            self._thread = threading.Thread(target=self._mqtt_loop, daemon=True)
            self._thread.start()

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to setup MQTT client: {e}")
            self._client = None

    def _mqtt_loop(self):
        """Function run in a separate thread to keep the MQTT loop running."""
        if not self._client:
            return
        if self.logger:
            self.logger.info("MQTT client loop started.")
        while not self._stop_event.is_set():
            try:
                rc = self._client.loop(timeout=1.0)
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    if self.logger:
                        self.logger.warning(f"MQTT loop returned error code: {rc}. Attempting to handle.")
                    # Paho will automatically handle reconnections,
                    # but we can log or handle specific cases if needed.
                    time.sleep(5)  # Wait before next loop iteration
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Exception in MQTT loop: {e}")
                # In case of a severe error, try to reconnect after a pause
                if not self._stop_event.is_set():
                    time.sleep(10)
                    try:
                        if not self._client.is_connected():
                            if self.logger:
                                self.logger.info("Attempting to reconnect MQTT client...")
                            self._client.reconnect()
                    except Exception as reconn_e:
                        if self.logger:
                            self.logger.error(f"Failed to manually reconnect MQTT: {reconn_e}")

        if self.logger:
            self.logger.info("MQTT client loop stopped.")
        if self._client.is_connected():
            if self.logger:
                self.logger.debug("Disconnecting MQTT client cleanly.")
            self._client.disconnect()

    def stop(self):
        """Stop the MQTT client and its loop thread."""
        if self.logger:
            self.logger.info("Stopping MQTT Energy Monitor...")
        self._stop_event.set()
        if self._client:
            # We dont disconnect here, loop_stop will handle it if necessary
            # Calling loop_stop waits for the thread to finish the current loop
            self._client.loop_stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)  # Wait for the thread to finish
            if self._thread.is_alive():
                if self.logger:
                    self.logger.warning("MQTT loop thread did not stop gracefully.")
        if self.logger:
            self.logger.info("MQTT Energy Monitor stopped.")

    def _on_log(self, client, userdata, level, buf):
        """Callback per i log interni di paho-mqtt."""
        # Mappa i livelli di paho a quelli di logging di Python se necessario
        # Maps the paho log levels to logger logging levels
        if level == mqtt.MQTT_LOG_ERR:
            if self.logger:
                self.logger.error(f"PAHO-MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            if self.logger:
                self.logger.warning(f"PAHO-MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            if self.logger:
                self.logger.info(f"PAHO-MQTT: {buf}")
        else:  # MQTT_LOG_DEBUG, MQTT_LOG_NOTICE
            if self.logger:
                self.logger.debug(f"PAHO-MQTT: {buf}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when connected to the MQTT broker."""
        if rc == 0:
            if self.logger:
                self.logger.info(f"Successfully connected to MQTT broker: {self.broker_host}:{self.broker_port}")
            self._connected.set()  # Connection successful, set the connected flag
            # Subscribe to configured topics
            for internal_name, topic in self.topics_map.items():
                if topic:
                    if self.logger:
                        self.logger.info(f"Subscribing to topic '{topic}' for '{internal_name}'")
                    # Use QoS 1 for better reliability if the broker supports it well
                    result, mid = client.subscribe(topic, qos=1)
                    if result != mqtt.MQTT_ERR_SUCCESS:
                        if self.logger:
                            self.logger.error(f"Failed to subscribe to topic '{topic}': {mqtt.error_string(result)}")
                    else:
                        if self.logger:
                            self.logger.debug(f"Subscription request sent for '{topic}' (MID: {mid})")

        else:
            if self.logger:
                self.logger.error(f"Failed to connect to MQTT broker: {mqtt.connack_string(rc)}")
            self._connected.clear()

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback when disconnected from the MQTT broker."""
        self._connected.clear()
        if self.logger:
            self.logger.warning(
                f"Disconnected from MQTT broker (rc: {rc}). Reconnection should be attempted automatically by Paho."
            )

    def _on_message(self, client, userdata, msg):
        """Callback when a message is received on a subscribed topic."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            if self.logger:
                self.logger.debug(f"MQTT message received: Topic='{topic}', Payload='{payload}'")

            # Find the internal sensor name for this topic
            internal_name = None
            for name, configured_topic in self.topics_map.items():
                # We can user `mqtt.topic_matches_sub` if we want to support wildcards in topics
                if configured_topic == topic:
                    internal_name = name
                    break

            if internal_name:
                # Parse the payload based on the internal sensor name
                parsed_value: Optional[Union[Watts, Percentage]] = None
                unit = self.units_map.get(internal_name, "W").lower()  # Default a Watts

                if internal_name in [
                    "solar_production",
                    "house_consumption",
                    "grid_power",
                    "battery_power",
                ]:
                    parsed_value = self._parse_power(payload, unit, topic)
                    # Apply conventions for grid and battery power
                    if parsed_value:
                        if internal_name == "grid_power":
                            if self.conventions.get("grid_positive_export", False):
                                parsed_value = Watts(parsed_value * -1)  # Positive for export
                        elif internal_name == "battery_power":
                            if not self.conventions.get("battery_positive_charge", True):
                                parsed_value = Watts(parsed_value * -1)  # Positive for charge

                elif internal_name == "battery_soc":
                    parsed_value = self._parse_percentage(payload, topic)

                else:
                    if self.logger:
                        self.logger.warning(f"Received message for unhandled internal sensor name: '{internal_name}'")

                # Update the internal state in a thread-safe manner
                if parsed_value is not None:
                    with self._lock:
                        self._latest_values[internal_name] = parsed_value
                        self._last_update_times[internal_name] = datetime.now(timezone.utc)  # Usa UTC
                        if self.logger:
                            self.logger.debug(
                                f"Stored '{internal_name}' = {parsed_value} "
                                f"(Timestamp: {self._last_update_times[internal_name]})"
                            )
                else:
                    if self.logger:
                        self.logger.warning(f"Could not parse value for topic '{topic}', payload '{payload}'")

            else:
                if self.logger:
                    self.logger.warning(f"Received message on unexpected topic: '{topic}'")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing MQTT message (Topic: {msg.topic}): {e}")

    def _parse_power(
        self,
        state: Optional[str],
        configured_unit: str,
        entity_id_for_log: str,
    ) -> Optional[Watts]:
        """Helper to parse power values from MQTT messages."""
        if state is None:
            return None
        try:
            value = float(state)
            if math.isnan(value):
                return None
            if configured_unit.lower() == "kw":
                value *= 1000
            elif configured_unit.lower() != "w":
                if self.logger:
                    self.logger.warning(
                        f"Unsupported unit '{configured_unit}' for topic '{entity_id_for_log}'. Assuming Watts."
                    )
            return Watts(value)
        except (ValueError, TypeError):
            return None

    def _parse_percentage(self, state: Optional[str], entity_id_for_log: str) -> Optional[Percentage]:
        """Helper to parse percentage values from MQTT messages."""
        if state is None:
            return None
        try:
            value = float(state)
            if math.isnan(value):
                return None
            return Percentage(max(0.0, min(100.0, value)))  # Clamp 0-100
        except (ValueError, TypeError):
            return None

    def get_current_energy_state(self) -> Optional[EnergyStateSnapshot]:
        """
        Give the latest energy state snapshot based on received MQTT messages.
        Checks if the data is too old and logs warnings if values are stale or missing."""
        if not self._connected.is_set():
            if self.logger:
                self.logger.warning("MQTT client not connected. Cannot provide energy state.")
            # We could try to read old values, but it's risky. Better to return None.
            return None

        # Access the latest values and timestamps in a thread-safe manner
        with self._lock:
            latest_values = self._latest_values.copy()
            last_update_times = self._last_update_times.copy()

        now = datetime.now(timezone.utc)
        snapshot_time = Timestamp(now.astimezone())  # Convert to local timezone for snapshot
        has_critical_error = False
        is_stale = False

        # Get the latest values and check if they are stale
        production, stale_prod = self._get_value("solar_production", latest_values, last_update_times, now)
        consumption, stale_cons = self._get_value("house_consumption", latest_values, last_update_times, now)
        grid_power, stale_grid = self._get_value("grid_power", latest_values, last_update_times, now)
        battery_soc, stale_soc = self._get_value("battery_soc", latest_values, last_update_times, now)
        battery_power, stale_power = self._get_value("battery_power", latest_values, last_update_times, now)

        is_stale = any([stale_prod, stale_cons, stale_grid, stale_soc, stale_power])

        # Check if critical data is missing (never received)
        if self.topics_map.get("solar_production") and production is None:
            if self.logger:
                self.logger.error(
                    f"Missing critical value: Solar Production (Topic: {self.topics_map['solar_production']})"
                )
            has_critical_error = True
        if self.topics_map.get("house_consumption") and consumption is None:
            if self.logger:
                self.logger.error(
                    f"Missing critical value: House Consumption (Topic: {self.topics_map['house_consumption']})"
                )
            has_critical_error = True
        if self.topics_map.get("grid_power") and grid_power is None:
            if self.logger:
                self.logger.error(f"Missing critical value: Grid Power (Topic: {self.topics_map['grid_power']})")
            has_critical_error = True
        # Battery is critical only if both SOC and Power are required and missing
        if self.topics_map.get("battery_soc") and self.topics_map.get("battery_power"):
            if battery_soc is None:
                if self.logger:
                    self.logger.error(f"Missing critical value: Battery SOC (Topic: {self.topics_map['battery_soc']})")
                has_critical_error = True
            if battery_power is None:
                if self.logger:
                    self.logger.error(
                        f"Missing critical value: Battery Power (Topic: {self.topics_map['battery_power']})"
                    )
                has_critical_error = True

        if has_critical_error:
            if self.logger:
                self.logger.error(
                    "One or more critical energy values were never received via MQTT. Cannot create snapshot."
                )
            return None

        if is_stale:
            if self.logger:
                self.logger.warning(
                    "One or more sensor values are stale. Using last known values, but they might be inaccurate."
                )
            # Decision: Continue with stale data or return None? For now, we continue.
            # if is_stale: return None # Safer option

        # Fill defaults if not configured or missing (but not critical)
        production = production if production is not None else Watts(0.0)
        consumption = consumption if consumption is not None else Watts(0.0)
        grid_power = grid_power if grid_power is not None else Watts(0.0)

        # Build BatteryState if possible
        battery_state: Optional[BatteryState] = None
        if battery_soc is not None and battery_power is not None and self.battery_capacity is not None:
            battery_state = BatteryState(
                state_of_charge=battery_soc,
                remaining_capacity=self.battery_capacity,
                current_power=battery_power,
                timestamp=snapshot_time,
            )
        elif self.topics_map.get("battery_soc"):
            if self.logger:
                self.logger.debug(
                    "Battery SOC topic configured, but full BatteryState cannot be created "
                    + "(missing power topic/value or static capacity setting?)."
                )

        load_state = LoadState(
            current_power=consumption,
            timestamp=snapshot_time,
        )
        grid_state = GridState(
            current_power=grid_power,
            timestamp=snapshot_time,
        )

        snapshot = EnergyStateSnapshot(
            production=production,
            consumption=load_state,
            battery=battery_state,
            grid=grid_state,
            external_source=None,
            timestamp=snapshot_time,
        )

        if self.logger:
            production_str: str = f"{snapshot.production:.0f}W" if snapshot.production else "N/A"
            consumption_str: str = f"{snapshot.consumption.current_power:.0f}W" if snapshot.consumption else "N/A"
            grid_str: str = f"{snapshot.grid.current_power:.0f}W" if snapshot.grid else "N/A"
            self.logger.info(
                f"MQTT Monitor: State Snapshot: Prod={production_str}, "
                f"Cons={consumption_str}, Grid={grid_str}, "
                f"SOC={snapshot.battery.state_of_charge if snapshot.battery else 'N/A'}%, "
                f"BattPwr={snapshot.battery.current_power if snapshot.battery else 'N/A'}W "
                f"(Stale: {is_stale})"
            )

        return snapshot

    def _get_value(
        self,
        name: str,
        latest_values: Dict[str, Any],
        last_update_times: Dict[str, datetime],
        now: datetime,
    ) -> Tuple[Optional[Any], bool]:
        """Helper to get the latest value and check if it's stale."""
        value = latest_values.get(name)
        last_update = last_update_times.get(name)
        stale = False
        # Only if topic is configured
        if self.topics_map.get(name):
            if value is None:
                if self.logger:
                    self.logger.warning(
                        f"No value received yet for sensor '{name}' (Topic: {self.topics_map.get(name)})"
                    )
                # Should this be considered an error only if it's a critical sensor?
                # For now, we do not consider it a critical error if it has NEVER been received
            elif last_update is None or (now - last_update) > self.max_data_age:
                if self.logger:
                    self.logger.warning(
                        f"Data for sensor '{name}' is stale (Last update: {last_update},"
                        f" Age: {now - last_update if last_update else 'N/A'})"
                    )
                stale = True
                # Should we consider stale data as unavailable for calculation?
                # It depends on criticality. For now, we use them but log a warning.
                # We could choose to return None for the value here.

        return value, stale
