# rgbw2_mqtt2http
Service that translates messages coming over MQTT topics into HTTP request to a Shelly RGBW2

## Installation

### System Requirements
First, ensure your system has the required packages:
```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv
```

### Service Installation
Clone the repository and install the service:
```bash
git clone https://github.com/dwarsdriewer/rgbw2_mqtt2http.git
cd rgbw2_mqtt2http
chmod +x install.sh
sudo ./install.sh
```

### Service Management
After installation, you can manage the service with these commands:
- Check service status: `sudo systemctl status rgbw2srv.service`
- View logs: `sudo journalctl -u rgbw2srv.service`
- Stop service: `sudo systemctl stop rgbw2srv.service`
- Start service: `sudo systemctl start rgbw2srv.service`
- Disable autostart: `sudo systemctl disable rgbw2srv.service`

The service will start automatically when the system boots up.