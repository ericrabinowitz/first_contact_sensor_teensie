# Missing Link Network Quick Reference Card

## Network Map
```
Device              IP Address      Username    Purpose
────────────────────────────────────────────────────────
Main Pi (Server)    192.168.4.1     pi         DHCP/DNS/MQTT/Controller
Pi Zero (NTP/RTC)   192.168.4.2     pi         Time Server with DS3231
Mango Router (AP)   192.168.4.___   admin      WiFi Access Point

WLED Controllers:
five_v_1            192.168.4.11    -          LED Controller
five_v_2            192.168.4.12    -          LED Controller  
twelve_v_1          192.168.4.13    -          LED Controller
spare_quinled       192.168.4.14    -          LED Controller

Teensy Boards:
teensy_1            192.168.4.21    -          Contact Sensor
teensy_2            192.168.4.22    -          Contact Sensor
elektra             192.168.4.23    -          Statue Controller
ariel               192.168.4.24    -          Statue Controller
sophia              192.168.4.25    -          Statue Controller
eros                192.168.4.26    -          Statue Controller
ultimo              192.168.4.27    -          Statue Controller
```

## WiFi Access
```
SSID:     _________________
Password: _________________
```

## SSH Commands
```bash
# From laptop/phone on WiFi:
ssh pi@192.168.4.1         # Main Pi
ssh pi@192.168.4.2         # Pi Zero NTP
ssh pi@rpi.local           # Alternative for main Pi
ssh pi@pi-ntp.local        # Alternative for Pi Zero

# Default password: raspberry (change this!)
```

## Quick Status Checks

### On Main Pi
```bash
# Check all services
controller.status           # Controller script
mosquitto.status           # MQTT broker
dnsmasq.status            # DHCP/DNS server
ntp.status                # Time sync status

# View logs
controller.logs           # Live controller logs
mosquitto.logs           # MQTT logs
ntp.monitor.logs         # NTP sync logs

# Network checks
leases                   # Show DHCP assignments
arp.local               # Show connected devices
ntp.check               # Test Pi Zero NTP

# Service control
controller.restart       # Restart controller
mosquitto.restart       # Restart MQTT
dnsmasq.restart        # Restart DHCP/DNS
```

### On Pi Zero
```bash
# Check RTC
sudo hwclock -r          # Read RTC time
sudo i2cdetect -y 1      # Verify RTC at 0x68

# Check NTP server
chronyc sources          # Show time sources
chronyc clients          # Show NTP clients
systemctl status chrony  # NTP server status
```

## Emergency Recovery

### Reset Mango Router
```
AP Mode → Router Mode:     Hold reset 4 seconds
Factory Reset:              Hold reset 10 seconds
Default WiFi SSID:          GL-MT300N-V2-XXX
Default WiFi Pass:          goodlife
Default Admin URL:          http://192.168.8.1
```

### Fix Time Sync
```bash
# On Pi Zero - Set RTC from system
sudo date -s "2025-08-22 15:30:00"
sudo hwclock -w

# On Main Pi - Force sync
sudo systemctl restart systemd-timesyncd
sudo /usr/local/bin/ntp-monitor.sh

# Check sync status
timedatectl status
```

### Network Not Working
```bash
# On Main Pi - Restart network stack
sudo systemctl restart NetworkManager
sudo systemctl restart dnsmasq

# Find devices manually
sudo arp-scan 192.168.4.0/24
ping 192.168.4.2  # Test Pi Zero
ping 192.168.4.11 # Test WLED
```

### Controller Not Running
```bash
# Check and restart
controller.status
controller.restart

# Run manually for debugging
cd ~/first_contact_sensor_teensie/raspberry_pi/controller
./controller.py
```

## Power Connections

### Main Pi
- Ethernet to switch/router
- Power via USB-C
- USB audio devices (if using)

### Pi Zero  
- USB-to-Ethernet adapter → Network
- Micro USB power (5V/2A)
- DS3231 RTC wired to GPIO

### Mango Router
- WAN port → Network switch
- Micro USB power (5V/2A)
- LAN port available for wired device

## DS3231 RTC Wiring
```
DS3231 → Pi Zero GPIO
─────────────────────
VCC    → Pin 1 (3.3V)
GND    → Pin 6 (Ground)
SDA    → Pin 3 (GPIO 2)
SCL    → Pin 5 (GPIO 3)
```

## Environment Variables

When NTP is synchronized, controller gets:
- `CONSERVE_POWER=1` - Enables power saving
- `NTP_SYNCED=true` - Time is accurate
- `NTP_SERVER=192.168.4.2` - Using Pi Zero

## MQTT Topics
```
missing_link/touch     # Contact detection
missing_link/haptic    # Haptic feedback
wled/{statue}/api      # LED control
```

## Test Commands

### Test MQTT
```bash
mosquitto_sub -t "#" -v                    # Monitor all topics
mosquitto_pub -t test -m "hello"           # Send test message
```

### Test Controller API
```bash
curl http://192.168.4.1:8080/info          # System info
curl http://192.168.4.1:8080/config        # Configuration
```

### Test WLED
```bash
curl http://192.168.4.11/json/state        # Get WLED state
```

## Backup Critical Info

Write these down before going to playa:
- [ ] WiFi SSID: _________________
- [ ] WiFi Password: _________________  
- [ ] Pi passwords: _________________
- [ ] Mango admin password: _________________
- [ ] Mango IP after AP mode: _________________

## Pre-Playa Checklist

- [ ] All Pis accessible via SSH
- [ ] RTC showing correct time
- [ ] NTP sync working (check CONSERVE_POWER)
- [ ] WiFi access working
- [ ] MQTT messages flowing
- [ ] Controller running on boot
- [ ] WLED controllers responding
- [ ] Teensy boards getting DHCP IPs
- [ ] Document all passwords
- [ ] Test power cycle recovery

## Contact Info

GitHub: https://github.com/ericrabinowitz/first_contact_sensor_teensie
Issues: Report at GitHub issues page

---
Generated: 2025-01-22 | Print and laminate for playa!