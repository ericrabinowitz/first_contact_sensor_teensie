# Raspberry Pi

All of the statues are orchestrated via 1 Raspberry Pi. It contains the following services:

- DHCP server
- DNS resolver
- MQTT broker
- Controller script

## Setup

When creating the initial image, make sure that username = pi, hostname = rpi.

```bash
ssh pi@rpi.local
sudo apt install -y git
cd ~
git clone https://github.com/ericrabinowitz/first_contact_sensor_teensie.git
cd ~/first_contact_sensor_teensie/raspberry_pi/setup
./setup.sh
```

## Update

```bash
cd ~/first_contact_sensor_teensie/raspberry_pi/setup
git pull
./setup.sh
```

## Debugging

### Controller script

1. Connect to the WiFi router or plug ethernet cable into switch.
1. Open your favorite terminal program.
1. Execute one of the following commands to get data from or configure the controller script.

```bash
# Get basic info
curl http://192.168.4.1:8080/info

# Get static config data
curl http://192.168.4.1:8080/config/static

# Get dynamic config data
curl http://192.168.4.1:8080/config/dynamic

# Turn on debug logging
curl -H "Content-Type: application/json" -X POST http://192.168.4.1:8080/debug \
  -d '{"debug":true}'

# Simulate linking
curl -H "Content-Type: application/json" -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"eros", "emitters":["elektra"]}'

# Simulate unlinking
curl -H "Content-Type: application/json" -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"eros", "emitters":[]}'

# Toggle the lights on and off
curl -H "Content-Type: application/json" -X POST http://192.168.4.1:8080/led/eros \
  -d '{"on":"t"}'

# Turn the haptic motor on
curl -H "Content-Type: application/json" -X POST http://192.168.4.1:8080/haptic/elektra
```

### Service Status / Logs

1. Connect to the WiFi router or plug ethernet cable into switch.
1. Open your favorite terminal program.
1. SSH into the Pi: `ssh pi@192.168.4.1`
1. Execute one of the following commands.

```bash
NetworkManager.status
NetworkManager.logs

mosquitto.status
mosquitto.logs

dnsmasq.status
dnsmasq.logs

controller.status
controller.logs
```

### Other

```bash
# Play an audio file
aplay ~/first_contact_sensor_teensie/audio_files/"Missing Link unSCruz active 1 Remi Wolf Polo Pan Hello.wav"

# Subscribe to a MQTT topic
mosquitto_sub -t "missing_link/contact"

# Send a MQTT message
mosquitto_pub -t "missing_link/contact" -m '{"detector":"eros", "emitters":["elektra"]}'
```

### Manually Configure Teensy Thresholds

You can update detection thresholds for individual statues by sending a minimal config via MQTT. Only specify the statue(s) and threshold(s) you want to change:

```bash
# Update sophia's threshold (more sensitive)
mosquitto_pub -h 192.168.4.1 -t "missing_link/config/response" -m '{"sophia": {"threshold": 0.005}}'

# Update multiple statues at once
mosquitto_pub -h 192.168.4.1 -t "missing_link/config/response" -m '{
  "sophia": {"threshold": 0.005},
  "ultimo": {"threshold": 0.015}
}'

# Or use a config file
cat > /tmp/sophia_threshold.json << 'EOF'
{
  "sophia": {
    "threshold": 0.005
  }
}
EOF
mosquitto_pub -h 192.168.4.1 -t "missing_link/config/response" -f /tmp/sophia_threshold.json
```

**How it works:**
- All Teensy boards receive the config message
- Each board updates its `STATUE_THRESHOLDS` array for the specified statue(s)
- Detectors targeting that statue automatically use the new threshold
- Only the `threshold` field is required - no need to specify `emit`, `detect`, `mac_address`, or `ip_address`

**Threshold values:**
- Lower = more sensitive (e.g., `0.005` detects weaker signals)
- Higher = less sensitive (e.g., `0.015` requires stronger signals)
- Default: `0.01`
- Valid range: `0.001` to `1.0`

**Example saved configs:**
```bash
# Pre-configured files in raspberry_pi/config/
~/first_contact_sensor_teensie/raspberry_pi/config/sophia_lower_threshold.json
~/first_contact_sensor_teensie/raspberry_pi/config/sophia_threshold_minimal.json
```

## Reference docs

- https://docs.google.com/document/d/107ZdOsc81E29lZZVTtqirHpqJKrvnqui0-EGSTGGslk/edit?tab=t.0
- https://docs.google.com/document/d/1Ke_J2RJw4KxdZ-_T9ig0PT2Xt90lASSOVepb4xZkUKM/edit?tab=t.0
- https://blog.dusktreader.dev/2025/03/29/self-contained-python-scripts-with-uv/
- https://docs.astral.sh/uv/
- https://www.raspberrypi.com/documentation/computers/configuration.html#audio-3
- https://www.raspberrypi.com/documentation/accessories/audio.html
