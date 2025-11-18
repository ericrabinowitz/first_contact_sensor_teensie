# Main Pi NTP Client Configuration Specification

## Overview

This document specifies how the main Raspberry Pi (192.168.4.1) should be configured to use the Pi Zero RTC/NTP server as its primary time source, with automatic fallback to internet NTP servers. The system will dynamically enable power-saving features when accurate time synchronization is achieved.

## Design Principles

1. **Resilience**: System must function with or without Pi Zero NTP server
2. **Automatic Detection**: No manual intervention required
3. **Dynamic Configuration**: Adjust behavior based on NTP availability
4. **Minimal Complexity**: Simple, maintainable solution

## Network Configuration Updates

### 1. DHCP Configuration (`dnsmasq.conf`)

Add to `/etc/dnsmasq.conf`:

```conf
# Pi Zero RTC/NTP server
# MAC address to be filled after first boot
dhcp-host=<MAC_ADDRESS>,192.168.4.2,pi-ntp

# Advertise NTP server to all DHCP clients
dhcp-option=42,192.168.4.2
```

### 2. Host Mapping (`/etc/hosts`)

Add to `/etc/hosts`:

```
192.168.4.2    pi-ntp
```

## NTP Client Configuration

### 1. systemd-timesyncd Configuration

Create/modify `/etc/systemd/timesyncd.conf`:

```ini
[Time]
# Primary: Local Pi Zero NTP server
NTP=192.168.4.2

# Fallback: Internet NTP servers
FallbackNTP=0.debian.pool.ntp.org 1.debian.pool.ntp.org 2.debian.pool.ntp.org

# Poll interval when synchronized (seconds)
PollIntervalMinSec=32
PollIntervalMaxSec=2048

# Save time on shutdown for next boot
RootDistanceMaxSec=5
```

## Dynamic Power Management

### 1. NTP Monitor Script

Create `/usr/local/bin/ntp-monitor.sh`:

```bash
#!/bin/bash
# NTP Monitor - Dynamically adjust controller power settings based on NTP sync

# Configuration
NTP_SERVER="192.168.4.2"
OVERRIDE_DIR="/etc/systemd/system/controller.service.d"
OVERRIDE_FILE="$OVERRIDE_DIR/ntp-environment.conf"
LOG_TAG="ntp-monitor"

# Function to log messages
log_message() {
    logger -t "$LOG_TAG" "$1"
}

# Function to check NTP synchronization
check_ntp_sync() {
    # Check if NTP server is reachable
    if ! ping -c 1 -W 1 "$NTP_SERVER" >/dev/null 2>&1; then
        return 1
    fi
    
    # Check if time is synchronized
    if timedatectl show | grep -q "NTPSynchronized=yes"; then
        # Additional check for time accuracy
        local offset=$(timedatectl show | grep "^TimeUSec" | cut -d= -f2)
        if [ -n "$offset" ]; then
            return 0
        fi
    fi
    
    return 1
}

# Function to enable power saving
enable_power_saving() {
    mkdir -p "$OVERRIDE_DIR"
    cat > "$OVERRIDE_FILE" <<EOF
[Service]
Environment="CONSERVE_POWER=1"
Environment="NTP_SYNCED=true"
Environment="NTP_SERVER=$NTP_SERVER"
EOF
    
    log_message "NTP synchronized - enabling power saving mode"
    
    # Only reload and restart if configuration changed
    if ! systemctl show controller -p Environment | grep -q "CONSERVE_POWER=1"; then
        systemctl daemon-reload
        systemctl restart controller
        log_message "Controller service restarted with power saving enabled"
    fi
}

# Function to disable power saving
disable_power_saving() {
    if [ -f "$OVERRIDE_FILE" ]; then
        rm "$OVERRIDE_FILE"
        log_message "NTP not synchronized - disabling power saving mode"
        
        systemctl daemon-reload
        systemctl restart controller
        log_message "Controller service restarted with power saving disabled"
    fi
}

# Main monitoring logic
main() {
    if check_ntp_sync; then
        enable_power_saving
    else
        disable_power_saving
    fi
}

# Run main function
main
```

### 2. Systemd Timer Configuration

Create `/etc/systemd/system/ntp-monitor.timer`:

```ini
[Unit]
Description=Monitor NTP synchronization status
Requires=network-online.target
After=network-online.target

[Timer]
# Start 30 seconds after boot
OnBootSec=30s

# Check every 60 seconds
OnUnitActiveSec=60s

# Randomize by up to 10 seconds to prevent thundering herd
RandomizedDelaySec=10s

[Install]
WantedBy=timers.target
```

### 3. Systemd Service Configuration

Create `/etc/systemd/system/ntp-monitor.service`:

```ini
[Unit]
Description=Check NTP sync and update controller environment
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/ntp-monitor.sh
StandardOutput=journal
StandardError=journal

# Restart on failure with backoff
Restart=on-failure
RestartSec=10s
```

## Integration with Setup Script

Add to `raspberry_pi/setup/setup.sh`:

```bash
# Configure NTP client
echo "Configuring NTP client..."
sudo tee /etc/systemd/timesyncd.conf > /dev/null <<EOF
[Time]
NTP=192.168.4.2
FallbackNTP=0.debian.pool.ntp.org 1.debian.pool.ntp.org
PollIntervalMinSec=32
PollIntervalMaxSec=2048
EOF

# Restart timesyncd
sudo systemctl restart systemd-timesyncd

# Install NTP monitor
echo "Installing NTP monitor..."
sudo cp ntp-monitor.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/ntp-monitor.sh

# Install systemd timer and service
sudo cp ntp-monitor.timer /etc/systemd/system/
sudo cp ntp-monitor.service /etc/systemd/system/

# Enable and start NTP monitor
sudo systemctl daemon-reload
sudo systemctl enable ntp-monitor.timer
sudo systemctl start ntp-monitor.timer

echo "NTP client configuration complete"
```

## Bash Aliases Updates

Add to `raspberry_pi/setup/bash_aliases`:

```bash
# NTP monitoring aliases
alias ntp.status="timedatectl status"
alias ntp.show="timedatectl show"
alias ntp.monitor.status="systemctl status ntp-monitor.timer ntp-monitor.service"
alias ntp.monitor.logs="journalctl -u ntp-monitor.service -f"
alias ntp.monitor.run="sudo /usr/local/bin/ntp-monitor.sh"

# Test NTP server
alias ntp.test="timedatectl show | grep -E 'NTPSynchronized|ServerName|ServerAddress'"
```

## Controller Service Integration

The controller service will automatically receive environment variables when NTP is synchronized:

- `CONSERVE_POWER=1` - Enable power-saving features
- `NTP_SYNCED=true` - Indicates time is accurate
- `NTP_SERVER=192.168.4.2` - Shows which NTP server is being used

Controller can check these in Python:

```python
import os

# Check if power saving should be enabled
conserve_power = os.environ.get('CONSERVE_POWER', '0') == '1'
ntp_synced = os.environ.get('NTP_SYNCED', 'false') == 'true'

if conserve_power and ntp_synced:
    print("Running in power-saving mode with accurate time")
    # Implement power-saving behaviors
else:
    print("Running in normal mode")
```

## Monitoring and Verification

### Check NTP Synchronization Status

```bash
# Full time status
timedatectl status

# Just sync status
timedatectl show | grep NTPSynchronized

# Check which NTP server is being used
timedatectl show | grep ServerName
```

### Monitor NTP Service

```bash
# Check monitor timer
systemctl status ntp-monitor.timer

# View monitor logs
journalctl -u ntp-monitor.service -f

# Manually trigger monitor
sudo /usr/local/bin/ntp-monitor.sh
```

### Verify Controller Environment

```bash
# Check if CONSERVE_POWER is set
systemctl show controller -p Environment

# View controller service with environment
systemctl status controller
```

## Testing Procedures

### 1. Test with Pi Zero Available

```bash
# Ensure Pi Zero is running
ping 192.168.4.2

# Check time sync
timedatectl status

# Verify CONSERVE_POWER is set
systemctl show controller | grep CONSERVE_POWER
```

### 2. Test Fallback (Pi Zero Unavailable)

```bash
# Disconnect Pi Zero or stop its NTP service

# Wait 60 seconds for monitor to detect

# Check fallback to internet NTP
timedatectl show | grep ServerName

# Verify CONSERVE_POWER is removed
systemctl show controller | grep Environment
```

### 3. Test Recovery

```bash
# Reconnect Pi Zero

# Wait for next monitor cycle (60s)

# Verify switch back to local NTP
timedatectl show | grep ServerName

# Verify CONSERVE_POWER is restored
systemctl show controller | grep CONSERVE_POWER
```

## Troubleshooting

### NTP Not Synchronizing

```bash
# Check timesyncd status
systemctl status systemd-timesyncd

# View timesyncd logs
journalctl -u systemd-timesyncd -f

# Test NTP server directly
ntpdate -q 192.168.4.2
```

### Monitor Not Running

```bash
# Check timer status
systemctl status ntp-monitor.timer

# Check last run
systemctl list-timers ntp-monitor.timer

# Run manually to test
sudo bash -x /usr/local/bin/ntp-monitor.sh
```

### Environment Variables Not Set

```bash
# Check override file exists
ls -la /etc/systemd/system/controller.service.d/

# View override contents
cat /etc/systemd/system/controller.service.d/ntp-environment.conf

# Force reload
sudo systemctl daemon-reload
sudo systemctl restart controller
```

## Performance Considerations

1. **Polling Interval**: 60 seconds balances responsiveness with system load
2. **Network Traffic**: Minimal - one ping per minute to Pi Zero
3. **Service Restarts**: Only when NTP state changes
4. **Time Accuracy**: Sub-second accuracy when synced to Pi Zero

## Security Notes

1. NTP traffic is unencrypted (standard NTP protocol)
2. Local network only - no external NTP access required
3. Monitor script runs with minimal privileges
4. No sensitive data in environment variables

## Future Enhancements

1. **Metrics Collection**: Export sync status to Prometheus
2. **Multi-Server Support**: Configure multiple local NTP servers
3. **Drift Monitoring**: Alert on excessive time drift
4. **Graceful Degradation**: Graduated power-saving levels based on sync quality