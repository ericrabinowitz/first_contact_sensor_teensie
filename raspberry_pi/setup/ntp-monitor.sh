#!/bin/bash
# NTP Monitor - Dynamically adjust controller power settings based on NTP sync
# This script checks if the Pi Zero NTP server is available and time is synchronized
# It then sets/unsets the CONSERVE_POWER environment variable for the controller service

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
    if timedatectl show --property=NTPSynchronized --value | grep -q "yes"; then
        return 0
    fi
    
    return 1
}

# Function to enable power saving
enable_power_saving() {
    mkdir -p "$OVERRIDE_DIR"
    
    # Create override file with environment variables
    cat > "$OVERRIDE_FILE" <<EOF
[Service]
Environment="CONSERVE_POWER=1"
Environment="NTP_SYNCED=true"
Environment="NTP_SERVER=$NTP_SERVER"
EOF
    
    log_message "NTP synchronized with $NTP_SERVER - enabling power saving mode"
    
    # Check if configuration actually changed
    if ! systemctl show controller -p Environment | grep -q "CONSERVE_POWER=1"; then
        systemctl daemon-reload
        
        # Only restart if controller is running
        if systemctl is-active --quiet controller; then
            systemctl restart controller
            log_message "Controller service restarted with power saving enabled"
        fi
    fi
}

# Function to disable power saving
disable_power_saving() {
    if [ -f "$OVERRIDE_FILE" ]; then
        rm "$OVERRIDE_FILE"
        log_message "NTP not synchronized - disabling power saving mode"
        
        systemctl daemon-reload
        
        # Only restart if controller is running
        if systemctl is-active --quiet controller; then
            systemctl restart controller
            log_message "Controller service restarted with power saving disabled"
        fi
    fi
}

# Main monitoring logic
main() {
    # Log current status
    local ntp_status=$(timedatectl show --property=NTPSynchronized --value)
    local system_time=$(timedatectl show --property=TimeUSec --value)
    
    log_message "Checking NTP status: NTPSynchronized=$ntp_status"
    
    if check_ntp_sync; then
        enable_power_saving
    else
        disable_power_saving
    fi
}

# Run main function
main