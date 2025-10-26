"""MQTT to HTTP bridge for Shelly RGBW2 devices."""

import sys
import ssl
import time
import signal
import logging
import requests
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Tuple, Callable, Any
from requests.auth import HTTPBasicAuth
from requests.models import Response
from paho.mqtt import client as mqtt_client
from random import randint

from config import (
    MQTT_BROKER_HOST, MQTT_BROKER_PORT,
    OAKLIGHT, NUMBERSIGN,
    TOPIC_OAKLIGHT_COMMAND, TOPIC_OAKLIGHT_SET, TOPIC_OAKLIGHT_STATUS,
    TOPIC_NUMBERSIGN_COMMAND, TOPIC_NUMBERSIGN_SET, TOPIC_NUMBERSIGN_STATUS,
    FIRST_RECONNECT_DELAY, RECONNECT_RATE, MAX_RECONNECT_COUNT, MAX_RECONNECT_DELAY
)

class CommandType(Enum):
    """Supported device commands."""
    ON = auto()
    OFF = auto()

@dataclass
class DeviceConfig:
    """Configuration for a Shelly RGBW2 device."""
    url: str
    command_topic: str
    set_topic: str
    status_topic: str
    name: str

@dataclass
class MQTTConfig:
    """MQTT broker configuration."""
    broker_host: str
    broker_port: int
    use_tls: bool = True
    qos: int = 1


def rgbw2_send_status(client: mqtt_client.Client, url: str, status: str) -> None:
    """Send status update to MQTT topic.
    
    Args:
        client: MQTT client instance
        url: Device URL to determine which topic to use
        status: Status message to publish
    """
    topic = TOPIC_OAKLIGHT_STATUS if url == OAKLIGHT else TOPIC_NUMBERSIGN_STATUS
    client.publish(topic, status, qos=1)

def rgbw2_send_command(url: str, command: str) -> Optional[Response]:
    """Send command to RGBW2 device.
    
    Args:
        url: Device URL
        command: Command to send (on/off)
    
    Returns:
        Response object if successful, None otherwise
    """
    logging.info(f"Sending command '{command}' to rgbw2")
    basic = HTTPBasicAuth('admin', shelly_password)
    try:
        response = requests.get(f"{url}/color/0?turn={command}", auth=basic)
        logging.info(f"Response: {response.status_code} - {response.text}")
        return response
    except Exception as err:
        logging.error(f"Failed to send command '{command}': {err}")
        return None
    
def rgbw2_set_brightness(url: str, brightness: int) -> Optional[Response]:
    """Set brightness level on RGBW2 device.
    
    Args:
        url: Device URL
        brightness: Brightness level (0-255)
    
    Returns:
        Response object if successful, None otherwise
    """
    logging.info(f"Setting brightness to '{brightness}' on rgbw2")
    basic = HTTPBasicAuth('admin', shelly_password)
    try:
        response = requests.get(f"{url}/color/0?white={brightness}", auth=basic)
        logging.info(f"Response: {response.status_code} - {response.text}")
        return response
    except Exception as err:
        logging.error(f"Failed to set brightness: {err}")
        return None

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def connect(broker_host: str, broker_port: int) -> mqtt_client.Client:
    """Connect to MQTT broker with TLS.
    
    Args:
        broker_host: MQTT broker hostname
        broker_port: MQTT broker port
    
    Returns:
        Connected MQTT client
    
    Raises:
        ValueError: If connection fails
    """
    client_id = f"mqtt-event-bus-{randint(0, 1000)}"
    logging.info(f"Connecting to MQTT broker {broker_host}:{broker_port} as {client_id}")
    
    client = mqtt_client.Client(callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2, client_id=client_id)
    client.enable_logger(logging.getLogger(__name__))
    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Configure TLS
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.set_ciphers("AES256-SHA")
    context.load_default_certs()
    client.tls_set_context(context)
    client.tls_insecure_set(True)  # TODO: Remove this in production
    
    try:
        client.connect(host=broker_host, port=broker_port)
        return client
    except Exception as e:
        raise ValueError(f"Failed to connect to MQTT broker: {e}")
    
def on_connect(
    client: mqtt_client.Client,
    userdata: None,
    flags: dict,
    reason_code: int,
    properties: mqtt_client.Properties
) -> None:    
    """Handle successful MQTT connection.
    
    Args:
        client: MQTT client instance
        userdata: User data (not used)
        flags: Connection flags
        reason_code: Connection result code
        properties: Connection properties
    """
    logging.info(f"Connected to MQTT broker with reason code: {reason_code}")
    
def on_connect_fail(client: mqtt_client.Client, userdata: None) -> None:
    """Handle MQTT connection failure.
    
    Args:
        client: MQTT client instance
        userdata: User data (not used)
    """
    logging.error("Failed to connect to MQTT broker")

def on_disconnect(client: mqtt_client.Client, flags, userdata: None, reason_code: int, properties) -> None:
    """Handle MQTT disconnection and implement reconnection logic.
    
    Args:
        client: MQTT client instance
        flags: Disconnection flags
        userdata: User data (not used)
        result_code: Disconnection reason code
        properties: Disconnection properties
    """
    logging.warning(f"Disconnected from MQTT broker with flag : {flags}, reason code: {reason_code} and properties: {properties}")
    
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info(f"Attempting reconnection in {reconnect_delay} seconds...")
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Successfully reconnected to MQTT broker")
            return
        except Exception as err:
            logging.error(f"Reconnection attempt failed: {err}")

        reconnect_delay = min(reconnect_delay * RECONNECT_RATE, MAX_RECONNECT_DELAY)
        reconnect_count += 1
        
    logging.error(f"Failed to reconnect after {reconnect_count} attempts")
    
# Command handlers for different message types
def handle_command(client: mqtt_client.Client, device_url: str, payload: str) -> None:
    """Handle on/off command for a device.
    
    Args:
        client: MQTT client instance
        device_url: URL of the device to control
        payload: Command payload ("on" or "off")
    """
    command = payload.lower()
    if command not in {"on", "off"}:
        logging.warning(f"Invalid command: {payload}")
        rgbw2_send_status(client, device_url, f'{{"error": "Invalid command: {payload}"}}')
        return
        
    logging.info(f"Setting device to {command}")
    response = rgbw2_send_command(device_url, command)
    rgbw2_send_status(client, device_url, response.text if response else '{"error": "Failed to send command"}')

def handle_brightness(client: mqtt_client.Client, device_url: str, payload: str) -> None:
    """Handle brightness setting for a device.
    
    Args:
        client: MQTT client instance
        device_url: URL of the device to control
        payload: Brightness value (0-100)
    """
    try:
        brightness = float(payload)
        if 0.0 <= brightness <= 100.0:
            logging.info(f"Setting brightness to {brightness}")
            response = rgbw2_set_brightness(device_url, int(brightness * 255.0 / 100.0))
            rgbw2_send_status(client, device_url, response.text if response else '{"error": "Failed to set brightness"}')
        else:
            logging.warning(f"Brightness value {brightness} out of range (0-100)")
            rgbw2_send_status(client, device_url, f'{{"error": "Brightness value {brightness} out of range (0-100)"}}')
    except ValueError:
        logging.warning(f"Invalid brightness value: {payload}")
        rgbw2_send_status(client, device_url, f'{{"error": "Invalid brightness value: {payload}"}}')

def on_message(client: mqtt_client.Client, userdata: None, message: mqtt_client.MQTTMessage) -> None:
    """Handle incoming MQTT messages.
    
    Args:
        client: MQTT client instance
        userdata: User data (not used)
        message: MQTT message
    """
    topic = message.topic
    payload = message.payload.decode()
    
    # Map topics to their handlers and device URLs
    topic_handlers = {
        TOPIC_OAKLIGHT_COMMAND: (handle_command, OAKLIGHT),
        TOPIC_OAKLIGHT_SET: (handle_brightness, OAKLIGHT),
        TOPIC_NUMBERSIGN_COMMAND: (handle_command, NUMBERSIGN),
        TOPIC_NUMBERSIGN_SET: (handle_brightness, NUMBERSIGN)
    }
    
    if handler_info := topic_handlers.get(topic):
        handler, device_url = handler_info
        handler(client, device_url, payload)
    else:
        logging.info(f"Unknown topic {topic} with payload {payload}")

class MQTTBridge:
    """MQTT to HTTP bridge service class."""
    
    def __init__(self):
        """Initialize the MQTT bridge service."""
        self._client: Optional[mqtt_client.Client] = None
        self._running: bool = False
        self._config = MQTTConfig(
            broker_host=MQTT_BROKER_HOST,
            broker_port=MQTT_BROKER_PORT
        )
        self._devices = {
            'oaklight': DeviceConfig(
                url=OAKLIGHT,
                command_topic=TOPIC_OAKLIGHT_COMMAND,
                set_topic=TOPIC_OAKLIGHT_SET,
                status_topic=TOPIC_OAKLIGHT_STATUS,
                name="Oak Light"
            ),
            'numbersign': DeviceConfig(
                url=NUMBERSIGN,
                command_topic=TOPIC_NUMBERSIGN_COMMAND,
                set_topic=TOPIC_NUMBERSIGN_SET,
                status_topic=TOPIC_NUMBERSIGN_STATUS,
                name="Number Sign"
            )
        }
    
    @property
    def client(self) -> Optional[mqtt_client.Client]:
        """Get the MQTT client instance."""
        return self._client
    
    @property
    def running(self) -> bool:
        """Check if the service is running."""
        return self._running
    
    def stop(self) -> None:
        """Stop the MQTT bridge service."""
        if self._client:
            logging.info("Disconnecting from MQTT broker...")
            self._client.disconnect()
            self._client.loop_stop()
        self._running = False
    
    def signal_handler(self, signum: int, frame) -> None:
        """Handle system signals for graceful shutdown.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = {signal.SIGTERM: 'SIGTERM', signal.SIGINT: 'SIGINT'}.get(signum, str(signum))
        logging.info(f"Received {signal_name}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def run(self) -> int:
        """Run the MQTT bridge service.
        
        Returns:
            int: Exit code (0 for success, 1 for error)
        """
        try:
            # Set up logging
            setup_logging()
            logging.info("Starting RGBW2 MQTT to HTTP bridge")
            
            # Set up signal handlers
            signal.signal(signal.SIGTERM, self.signal_handler)
            signal.signal(signal.SIGINT, self.signal_handler)
            
            # Connect to MQTT broker
            self._client = connect(
                broker_host=self._config.broker_host,
                broker_port=self._config.broker_port
            )
            
            # Subscribe to all control topics
            topics = [
                (device.command_topic, self._config.qos)
                for device in self._devices.values()
            ] + [
                (device.set_topic, self._config.qos)
                for device in self._devices.values()
            ]
            
            self._client.subscribe(topics)
            self._running = True
            
            logging.info("Service started successfully")
            self._client.loop_forever()
            return 0
            
        except Exception as e:
            logging.error(f"Service failed: {e}")
            self.stop()
            return 1

def read_shelly_password() -> str:
    """Read Shelly password from configuration file.
    
    Returns:
        str: The password read from the file
        
    Raises:
        SystemExit: If file cannot be read or is empty
    """
    password_file = os.path.expanduser("~/.config/rgbw2_mqtt2http/shelly_password.txt")
    
    try:
        with open(password_file, 'r') as f:
            if password := f.read().strip():  # walrus operator for assignment in if statement
                return password
            logging.error("Password file is empty")
            sys.exit(1)
    except FileNotFoundError:
        logging.error(f"Password file not found: {password_file}")
        sys.exit(1)
    except PermissionError:
        logging.error(f"No read permission for password file: {password_file}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error reading password file: {e}")
        sys.exit(1)


def main() -> int:
    """Main entry point for the service.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    bridge = None
    try:
        bridge = MQTTBridge()
        return bridge.run()
    except KeyboardInterrupt:
        if bridge:
            bridge.stop()
        return 0
    except Exception as e:
        logging.error(f"Service failed: {e}")
        if bridge:
            bridge.stop()
        return 1

# Initialize global state
shelly_password = read_shelly_password()
        
if __name__ == "__main__":
    sys.exit(main())