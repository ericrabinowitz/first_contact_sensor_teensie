#!/bin/bash
# Pi Zero RTC/NTP Server Setup Script
# Setup a Raspberry Pi Zero as an RTC/NTP server with DS3231 module
# Run with: bash pi_zero_rtc_ntp_setup.sh

set -e  # Exit on error

echo "======================================"
echo "Pi Zero RTC/NTP Server Setup"
echo "======================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# 1. Enable I2C interface
print_status "Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# 2. Install required packages
print_status "Installing required packages..."
sudo apt update
sudo apt install -y i2c-tools chrony

# 3. Load RTC kernel module
print_status "Loading RTC kernel module..."
sudo modprobe rtc-ds1307

# Check if module is already in /etc/modules
if ! grep -q "^rtc-ds1307" /etc/modules; then
    echo "rtc-ds1307" | sudo tee -a /etc/modules
    print_status "Added rtc-ds1307 to /etc/modules"
else
    print_status "rtc-ds1307 already in /etc/modules"
fi

# 4. Test I2C detection
print_status "Checking for I2C devices..."
if sudo i2cdetect -y 1 | grep -q "68"; then
    print_status "Found device at address 0x68 (DS3231)"
else
    print_warning "DS3231 not detected at address 0x68"
    print_warning "Please check your wiring:"
    echo "  VCC -> Pin 1 (3.3V)"
    echo "  GND -> Pin 6 (Ground)"
    echo "  SDA -> Pin 3 (GPIO 2)"
    echo "  SCL -> Pin 5 (GPIO 3)"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 5. Register DS3231 device
print_status "Registering DS3231 RTC..."
if [ ! -e /sys/class/i2c-adapter/i2c-1/1-0068 ]; then
    echo "ds1307 0x68" | sudo tee /sys/class/i2c-adapter/i2c-1/new_device
else
    print_status "DS3231 already registered"
fi

# 6. Test RTC hardware
print_status "Testing RTC hardware..."
if sudo hwclock -r 2>/dev/null; then
    print_status "RTC hardware working correctly"
    echo "  Current RTC time: $(sudo hwclock -r)"
else
    print_error "RTC hardware test failed"
    print_warning "Continuing with setup..."
fi

# 7. Create systemd service for RTC initialization
print_status "Creating RTC initialization service..."
sudo tee /etc/systemd/system/rtc-ds3231.service > /dev/null <<'EOF'
[Unit]
Description=Initialize DS3231 RTC
Before=chrony.service
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'if [ ! -e /sys/class/i2c-adapter/i2c-1/1-0068 ]; then echo ds1307 0x68 > /sys/class/i2c-adapter/i2c-1/new_device; fi'
ExecStart=/sbin/hwclock -s
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable rtc-ds3231.service
print_status "RTC initialization service enabled"

# 8. Configure chrony as NTP server
print_status "Configuring chrony NTP server..."

# Backup existing config
if [ -f /etc/chrony/chrony.conf ]; then
    sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.backup
    print_status "Backed up existing chrony.conf"
fi

sudo tee /etc/chrony/chrony.conf > /dev/null <<'EOF'
# Pi Zero RTC/NTP Server Configuration
# Using DS3231 RTC module

# RTC configuration
rtcfile /var/lib/chrony/chrony.rtc
rtcsync
# Automatically trim RTC every 10 seconds when synchronized
rtcautotrim 10

# Allow local network clients
allow 192.168.4.0/24

# Serve time even when not synchronized to internet
# Stratum 10 indicates we're a local time source
local stratum 10

# Internet NTP servers for initial sync (when available)
# These are used to set the RTC initially and keep it accurate
pool 0.debian.pool.ntp.org iburst
pool 1.debian.pool.ntp.org iburst
pool 2.debian.pool.ntp.org iburst
pool 3.debian.pool.ntp.org iburst

# Logging
log tracking measurements statistics
logdir /var/log/chrony

# Allow the system to step the clock during first three updates
# if the adjustment is larger than 1 second
makestep 1.0 3

# Enable hardware timestamping on all interfaces that support it
#hwtimestamp *

# Increase the minimum number of selectable sources required to adjust
# the system clock
#minsources 2

# Specify the file to record drift rate
driftfile /var/lib/chrony/chrony.drift

# Save NTS keys and cookies
ntsdumpdir /var/lib/chrony
EOF

print_status "Chrony NTP server configured"

# 9. Configure static IP address
print_status "Configuring static IP address (192.168.4.2)..."

# Check which network management system is in use
if systemctl is-active --quiet NetworkManager; then
    # NetworkManager is active
    print_status "Configuring with NetworkManager..."
    
    # Check if connection already exists
    if nmcli con show "eth0-static" &>/dev/null; then
        sudo nmcli con delete "eth0-static"
    fi
    
    sudo nmcli con add type ethernet con-name eth0-static ifname eth0 \
        ip4 192.168.4.2/24 gw4 192.168.4.1 \
        ipv4.dns "192.168.4.1" \
        ipv4.method manual \
        connection.autoconnect yes
    
    print_status "NetworkManager static IP configured"
    
elif [ -f /etc/dhcpcd.conf ]; then
    # dhcpcd is being used
    print_status "Configuring with dhcpcd..."
    
    # Backup existing config
    sudo cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
    
    # Remove any existing eth0 configuration
    sudo sed -i '/^interface eth0/,/^$/d' /etc/dhcpcd.conf
    
    # Add new configuration
    cat << 'EOF' | sudo tee -a /etc/dhcpcd.conf > /dev/null

# Static IP configuration for NTP server
interface eth0
static ip_address=192.168.4.2/24
static routers=192.168.4.1
static domain_name_servers=192.168.4.1
EOF
    
    print_status "dhcpcd static IP configured"
else
    print_warning "Could not determine network configuration method"
    print_warning "Please manually configure static IP: 192.168.4.2/24"
fi

# 10. Set system time from RTC (if available)
if sudo hwclock -r 2>/dev/null; then
    print_status "Setting system time from RTC..."
    sudo hwclock -s
    print_status "System time set from RTC"
else
    print_warning "Could not read RTC, using system time"
    # Set RTC from system time if NTP is synchronized
    if timedatectl show | grep -q "NTPSynchronized=yes"; then
        print_status "Setting RTC from system time..."
        sudo hwclock -w
    fi
fi

# 11. Restart chrony service
print_status "Restarting chrony service..."
sudo systemctl restart chrony
sleep 2

# 12. Verification
echo ""
echo "======================================"
echo "Setup Complete - Verification"
echo "======================================"
echo ""

# Check RTC
echo "RTC Status:"
if sudo hwclock -r 2>/dev/null; then
    sudo hwclock -r
else
    print_error "RTC not accessible"
fi
echo ""

# Check Chrony
echo "NTP Server Status:"
if systemctl is-active --quiet chrony; then
    print_status "Chrony service is running"
    echo ""
    echo "Time sources:"
    chronyc sources 2>/dev/null || print_warning "Chrony not ready yet"
    echo ""
    echo "Chrony tracking:"
    chronyc tracking 2>/dev/null || print_warning "Chrony not ready yet"
else
    print_error "Chrony service is not running"
fi
echo ""

# Check network
echo "Network Configuration:"
ip addr show eth0 2>/dev/null | grep "inet " || print_warning "No IP address on eth0 yet"
echo ""

# Check if listening on NTP port
echo "NTP Port Status:"
if sudo ss -ulnp | grep -q ":123"; then
    print_status "Listening on port 123 (NTP)"
else
    print_warning "Not yet listening on NTP port"
fi

# Final instructions
echo ""
echo "======================================"
echo "Next Steps"
echo "======================================"
echo ""
echo "1. Reboot to ensure all settings take effect:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify NTP server:"
echo "   chronyc sources"
echo "   chronyc clients"
echo ""
echo "3. Test from another device on the network:"
echo "   ntpdate -q 192.168.4.2"
echo ""
echo "4. Monitor RTC drift over time:"
echo "   sudo hwclock --adjust"
echo ""
print_status "Setup script completed successfully!"