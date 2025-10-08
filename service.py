import sys
import ssl
import time
import logging
import requests
from requests.auth import HTTPBasicAuth

from paho.mqtt import client as mqtt_client
from random import randint
import os

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

OAKLIGHT = "http://192.168.2.48"
NUMBERSIGN = "http://192.168.2.64"


def connect(broker_host: str, broker_port: int) -> mqtt_client.Client:
    client_id = f"mqtt-event-bus-{randint(0, 1000)}"
    client = mqtt_client.Client(callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2, client_id=client_id)
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    client.enable_logger(logger)
    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail
    client.on_message = on_message
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.set_ciphers("AES256-SHA")
    context.load_default_certs()
    client.tls_set_context(context)
    client.tls_insecure_set(True)
    client.connect(host = broker_host, port=broker_port)
    return client
    
def on_connect(client: mqtt_client.Client, userdata, flags, reason_code, properties):    
    logging.info(f"connected! Reason code: '{reason_code}'")
    
def on_connect_fail(client, userdata):
    logging.info("connection to MQTT broker failed")

def on_disconnect(client, userdata, result_code):
    logging.info(f"Disconnected with result code: '{result_code}'")
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info(f"Reconnecting in {reconnect_delay} seconds...")
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            return
        except Exception as err:
            logging.error(f"{err}. Reconnect failed. Retrying...")

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info(f"Reconnect failed after {reconnect_count} attempts. Exiting...")
    
def on_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode()
    if topic == "garden/oaklight/command":
        if payload == "ON" or payload == "on":
            logging.info("Oak light on")
            rgbw2_send_command(OAKLIGHT, "on")
        elif payload == "OFF" or payload == "off":
            logging.info("Oak light off")
            rgbw2_send_command(OAKLIGHT, "off")
    elif topic == "garden/oaklight/set":
        try:
            brightness = int(payload)
            if 0 <= brightness <= 100:
                logging.info(f"Set oak light brightness to {brightness}")
                rgbw2_set_brightness(OAKLIGHT, brightness)
            else:
                logging.info(f"Brightness value {brightness} out of range (0-100)")
        except ValueError:
            logging.info(f"Invalid brightness value: {payload}")
    elif topic == "carport/numbersign/command":
        if payload == "ON" or payload == "on":
            logging.info("Number sign on")
            rgbw2_send_command(NUMBERSIGN, "on")
        elif payload == "OFF" or payload == "off":
            logging.info("Number sign off")
            rgbw2_send_command(NUMBERSIGN, "off")
    elif topic == "carport/numbersign/set":
        try:
            brightness = int(payload)
            if 0 <= brightness <= 255:
                logging.info(f"Set number sign brightness to {brightness}")
                rgbw2_set_brightness(NUMBERSIGN, brightness)
            else:
                logging.info(f"Brightness value {brightness} out of range (0-100)")
        except ValueError:
            logging.info(f"Invalid brightness value: {payload}")
    else:   
        logging.info(f"Unknown topic {topic} with payload {payload}")

def main():
    try:
        client = connect(broker_host="raspi2.fritz.box", broker_port=8883)
        client.on_disconnect = on_disconnect;
        client.on_connect_fail = on_connect_fail;
        client.subscribe("garden/oaklight/command", qos=1)
        client.subscribe("garden/oaklight/set", qos=1)
        client.subscribe("carport/numbersign/command", qos=1)
        client.subscribe("carport/numbersign/set", qos=1)
        client.loop_forever()
        return 0
    except ValueError as ve:
        return str(ve)

def rgbw2_send_command(url: str, command: str):
    logging.info(f"Sending command '{command}' to rgbw2")
    password = os.environ.get("SHELLY_PASSWORD")
    print("password:", password)
    basic = HTTPBasicAuth('admin', password)
    try:
        response = requests.get(f"{url}/color/0?turn={command}", auth=basic)
        logging.info(f"Response: {response.status_code} - {response.text}")
    except Exception as err:
        logging.error(f"Failed to send command '{command}': {err}")
    
def rgbw2_set_brightness(url: str, brightness: int):
    logging.info(f"Setting brightness to '{brightness}' on rgbw2")
    password = os.environ.get("SHELLY_PASSWORD")
    basic = HTTPBasicAuth('admin', password)
    try:
        response = requests.get(f"{url}/color/0?white={brightness}", auth=basic)
        logging.info(f"Response: {response.status_code} - {response.text}")
    except Exception as err:
        logging.error(f"Failed to set brightness: {err}")

if __name__ == "__main__":
    sys.exit(main())