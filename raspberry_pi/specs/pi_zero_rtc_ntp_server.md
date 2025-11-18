# Pi Zero RTC/NTP Server Setup Specification

## Overview

This document specifies the configuration of a Raspberry Pi Zero as a dedicated RTC (Real-Time Clock) and NTP (Network Time Protocol) server for the Missing Link art installation. The Pi Zero will use a DS3231 RTC module to maintain accurate time even during power outages and serve as the primary time source for all devices on the network.

## Hardware Requirements

- Raspberry Pi Zero W or Pi Zero 2 W
- DS3231 RTC Module (3.3V/5V compatible)
- I2C connections:
  - VCC to 3.3V (Pin 1)
  - GND to Ground (Pin 6)
  - SDA to GPIO 2 (Pin 3)
  - SCL to GPIO 3 (Pin 5)

## Network Configuration

- **Static IP**: 192.168.4.2
- **Hostname**: pi-ntp
- **Gateway**: 192.168.4.1 (main Pi)
- **Services**: NTP server on port 123 (UDP)

## Setup Script

Create `/home/pi/setup_rtc_ntp.sh`:

```bash
#!/bin/bash
# Pi Zero RTC/NTP Server Setup Script
# Run with: bash setup_rtc_ntp.sh

set -e  # Exit on error

echo "Setting up Pi Zero as RTC/NTP server..."

# 1. Enable I2C interface
echo "Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# 2. Install required packages
echo "Installing required packages..."
sudo apt update
sudo apt install -y i2c-tools chrony

# 3. Load RTC kernel module
echo "Loading RTC kernel module..."
sudo modprobe rtc-ds1307
echo "rtc-ds1307" | sudo tee -a /etc/modules

# 4. Register DS3231 device (at I2C address 0x68)
echo "Registering DS3231 RTC..."
echo "ds1307 0x68" | sudo tee /sys/class/i2c-adapter/i2c-1/new_device

# 5. Test RTC hardware
echo "Testing RTC hardware..."
if sudo hwclock -r; then
    echo "RTC hardware detected successfully"
else
    echo "WARNING: RTC hardware not detected - check connections"
fi

# 6. Configure automatic RTC initialization on boot
echo "Configuring boot-time RTC initialization..."
sudo tee /etc/systemd/system/rtc-ds3231.service > /dev/null <<EOF
[Unit]
Description=Initialize DS3231 RTC
Before=chrony.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo ds1307 0x68 > /sys/class/i2c-adapter/i2c-1/new_device'
ExecStart=/sbin/hwclock -s
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable rtc-ds3231.service

# 7. Configure chrony as NTP server
echo "Configuring chrony NTP server..."
sudo tee /etc/chrony/chrony.conf > /dev/null <<'EOF'
# DS3231 RTC configuration
rtcfile /var/lib/chrony/chrony.rtc
rtcsync
rtcautotrim 10

# Allow local network clients
allow 192.168.4.0/24

# Serve time even when not synchronized to internet
local stratum 10

# Internet NTP servers for initial sync (when available)
pool 0.debian.pool.ntp.org iburst
pool 1.debian.pool.ntp.org iburst

# Log tracking
log tracking measurements statistics
EOF

# 8. Configure static IP address
echo "Configuring static IP (192.168.4.2)..."
sudo tee /etc/dhcpcd.conf > /dev/null <<EOF
interface eth0
static ip_address=192.168.4.2/24
static routers=192.168.4.1
static domain_name_servers=192.168.4.1
EOF

# Alternative for systems using NetworkManager
if command -v nmcli &> /dev/null; then
    sudo nmcli con add type ethernet con-name eth0-static ifname eth0 \
        ip4 192.168.4.2/24 gw4 192.168.4.1
fi

# 9. Set system time from RTC
echo "Setting system time from RTC..."
sudo hwclock -s

# 10. Restart services
echo "Restarting services..."
sudo systemctl restart chrony

# 11. Verification
echo ""
echo "=== Setup Complete ==="
echo "Verifying configuration..."
echo ""
echo "RTC Time:"
sudo hwclock -r
echo ""
echo "NTP Server Status:"
chronyc sources
echo ""
echo "Listening on port 123:"
sudo ss -ulnp | grep :123
echo ""
echo "Please reboot to ensure all settings take effect:"
echo "sudo reboot"
```

## Chrony NTP Server Configuration

The chrony configuration (`/etc/chrony/chrony.conf`) provides:

1. **RTC Integration**: Uses DS3231 as local time reference
2. **Local Network Service**: Serves time to 192.168.4.0/24 subnet
3. **Offline Operation**: Continues serving time even without internet
4. **Automatic Trimming**: Adjusts RTC drift over time

## Service Configuration

### RTC Initialization Service

`/etc/systemd/system/rtc-ds3231.service`:
- Initializes DS3231 on boot
- Syncs system time from RTC
- Runs before chrony starts

## Testing and Verification

### Initial Setup Tests

```bash
# Test I2C connection
sudo i2cdetect -y 1  # Should show device at 0x68

# Test RTC read/write
sudo hwclock -r      # Read time from RTC
sudo hwclock -w      # Write system time to RTC

# Test NTP server
chronyc sources      # Show time sources
chronyc clients      # Show connected clients
chronyc tracking     # Show synchronization status
```

### Monitoring Commands

```bash
# Check if NTP is serving time
sudo ss -ulnp | grep :123

# Monitor time drift
chronyc sourcestats

# Check RTC battery (if voltage drops below 3V, replace CR2032)
# Note: DS3231 has built-in temperature compensation
```

## Power Management

The DS3231 module includes:
- CR2032 battery backup (2-3 year lifespan)
- Temperature-compensated crystal oscillator (TCXO)
- Accuracy: ±2ppm from 0°C to +40°C (±1 minute per year)

## Integration with Main Pi

The main Pi will:
1. Request IP 192.168.4.2 via DHCP reservation
2. Use this Pi Zero as primary NTP server
3. Fall back to internet NTP if unavailable
4. Adjust CONSERVE_POWER based on sync status

## Troubleshooting

### RTC Not Detected
```bash
# Check I2C is enabled
sudo raspi-config nonint get_i2c  # Should return 0

# Check connections
sudo i2cdetect -y 1  # Look for device at 0x68

# Check kernel module
lsmod | grep rtc
```

### NTP Not Serving
```bash
# Check chrony is running
systemctl status chrony

# Check firewall (if enabled)
sudo iptables -L -n | grep 123

# Test from another device
ntpdate -q 192.168.4.2
```

### Time Drift Issues
```bash
# Check RTC battery voltage
# Manual RTC calibration if needed
sudo hwclock --systohc  # Set RTC from system
sudo hwclock --adjust   # Adjust for systematic drift
```

## Future Enhancements

1. **GPS Module**: Add GPS for stratum 1 time source
2. **Monitoring**: Add Prometheus metrics for time accuracy
3. **Redundancy**: Configure second Pi Zero as backup NTP
4. **PPS Signal**: Use pulse-per-second for microsecond accuracy