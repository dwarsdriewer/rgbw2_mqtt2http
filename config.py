"""Configuration for the RGBW2 MQTT to HTTP bridge."""

# MQTT Configuration
MQTT_BROKER_HOST = "raspi2.fritz.box"
MQTT_BROKER_PORT = 8883

# Device Configuration
OAKLIGHT = "http://192.168.2.48"
NUMBERSIGN = "http://192.168.2.64"

# MQTT Topics
TOPIC_OAKLIGHT_COMMAND = "garden/oaklight/command"
TOPIC_OAKLIGHT_SET = "garden/oaklight/set"
TOPIC_OAKLIGHT_STATUS = "garden/oaklight/status"
TOPIC_NUMBERSIGN_COMMAND = "carport/numbersign/command"
TOPIC_NUMBERSIGN_SET = "carport/numbersign/set"
TOPIC_NUMBERSIGN_STATUS = "carport/numbersign/status"

# Reconnection Configuration
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60