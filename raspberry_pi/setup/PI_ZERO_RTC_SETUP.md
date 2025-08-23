# Pi Zero RTC/NTP Server Setup Instructions

## Quick Start

### Hardware Setup

1. **Connect DS3231 RTC Module to Pi Zero:**
   - VCC → Pin 1 (3.3V)
   - GND → Pin 6 (Ground)  
   - SDA → Pin 3 (GPIO 2)
   - SCL → Pin 5 (GPIO 3)

2. **Connect Ethernet** to Pi Zero (using USB-to-Ethernet adapter if needed)

### Software Setup

1. **Fresh Raspberry Pi OS Installation:**
   ```bash
   # Flash Raspberry Pi OS Lite to SD card
   # Enable SSH by creating empty 'ssh' file in boot partition
   ```

2. **Initial Connection:**
   ```bash
   # Connect via SSH (use default hostname initially)
   ssh pi@raspberrypi.local
   ```

3. **Run Setup Script:**
   ```bash
   # Clone the repository
   git clone https://github.com/ericrabinowitz/first_contact_sensor_teensie.git
   cd first_contact_sensor_teensie/raspberry_pi/setup
   
   # Run the Pi Zero RTC/NTP setup
   bash pi_zero_rtc_ntp_setup.sh
   
   # Reboot when prompted
   sudo reboot
   ```

## Verification

After reboot, verify the setup:

### 1. Check RTC Hardware
```bash
# Read time from RTC
sudo hwclock -r

# Check I2C device
sudo i2cdetect -y 1
# Should show device at address 0x68
```

### 2. Check NTP Server
```bash
# Check chrony is running
systemctl status chrony

# View NTP sources
chronyc sources

# Check for clients
chronyc clients

# Verify listening on NTP port
sudo ss -ulnp | grep :123
```

### 3. Check Network Configuration
```bash
# Verify static IP
ip addr show eth0
# Should show 192.168.4.2/24
```

### 4. Test from Main Pi
```bash
# On the main Pi (192.168.4.1), test NTP server
ntpdate -q 192.168.4.2

# Or using chronyc
chronyc sources
```

## Manual Configuration

If the automatic setup script fails, you can configure manually:

### 1. Enable I2C
```bash
sudo raspi-config nonint do_i2c 0
```

### 2. Install Packages
```bash
sudo apt update
sudo apt install -y i2c-tools chrony
```

### 3. Setup RTC
```bash
# Load kernel module
sudo modprobe rtc-ds1307
echo "rtc-ds1307" | sudo tee -a /etc/modules

# Register device
echo "ds1307 0x68" | sudo tee /sys/class/i2c-adapter/i2c-1/new_device

# Copy service file
sudo cp rtc-ds3231.service /etc/systemd/system/
sudo systemctl enable rtc-ds3231.service
```

### 4. Configure Chrony
```bash
# Copy configuration
sudo cp chrony-ntp-server.conf /etc/chrony/chrony.conf
sudo systemctl restart chrony
```

### 5. Set Static IP

For NetworkManager:
```bash
sudo nmcli con add type ethernet con-name eth0-static ifname eth0 \
    ip4 192.168.4.2/24 gw4 192.168.4.1
```

For dhcpcd:
```bash
# Edit /etc/dhcpcd.conf and add:
interface eth0
static ip_address=192.168.4.2/24
static routers=192.168.4.1
static domain_name_servers=192.168.4.1
```

## Troubleshooting

### RTC Not Detected

1. Check wiring connections
2. Verify I2C is enabled: `sudo raspi-config nonint get_i2c`
3. Check for device: `sudo i2cdetect -y 1`

### NTP Server Not Working

1. Check chrony status: `systemctl status chrony`
2. View logs: `journalctl -u chrony -f`
3. Verify firewall allows port 123: `sudo iptables -L -n`

### Time Not Syncing

1. Check RTC battery (should be 3V)
2. Manually sync: `sudo hwclock -w` (write system time to RTC)
3. Check chrony tracking: `chronyc tracking`

## Maintenance

### Battery Replacement

The DS3231 uses a CR2032 battery that typically lasts 2-3 years:

1. Power down Pi Zero
2. Replace CR2032 battery
3. Power up and set time: `sudo hwclock -w`

### Monitoring Accuracy

```bash
# Check time drift
chronyc sourcestats

# View RTC drift
sudo hwclock --adjust

# Monitor temperature (affects accuracy)
cat /sys/class/hwmon/hwmon0/temp1_input
```

### Log Files

- Chrony logs: `/var/log/chrony/`
- System logs: `journalctl -u rtc-ds3231 -u chrony`

## Integration with Main Pi

The main Pi will automatically use this NTP server when available. No configuration needed on this Pi Zero beyond the setup above.

See `main_pi_ntp_client_config.md` for main Pi configuration details.