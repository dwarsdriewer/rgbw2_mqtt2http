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
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

mkdir -p ~/.config/rgbw2_mqtt2http/
echo "top_secret_password" > ~/.config/rgbw2_mqtt2http/shelly_password.txt
chmod 600 ~/.config/rgbw2_mqtt2http/shelly_password.txt

mkdir ~/.config/systemd/user
nano ~/.config/systemd/user/rgbw2.service
```
Content:
```
[Unit]
Description=Shelly RGBW2 MQTT to HTTP mapper service
After=network.target

[Service]
ExecStart=/home/tbeuck/python/rgbw2_mqtt2http/venv/bin/python /home/tbeuck/python/rgbw2_mqtt2http/service.py --password-file=/home/tbeuck/.config/rgbw2_mqtt2http/shelly_password.txt
WorkingDirectory=/home/tbeuck/python/rgbw2_mqtt2http/
Restart=on-failure
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

```
systemctl --user daemon-reload
systemctl --user enable rgbw2.service
```

### Service Management
After installation, you can manage the service with these commands:
- Enable service: `systemctl --user enable rgbw2.service`
- Check service status: `systemctl --user status rgbw2.service`
- View logs: `journalctl --user -u rgbw2.service`
- Stop service: `systemctl --user stop rgbw2.service`
- Start service: `systemctl --user start rgbw2.service`
- Disable autostart: `systemctl --user disable rgbw2.service`

The service will start automatically when the system boots up.