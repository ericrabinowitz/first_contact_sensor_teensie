#!/usr/bin/env bash

# This script configures Openbox to maximize the Missing Link Status Monitor terminal window
# It adds an application rule to the Openbox configuration file

set -e

OPENBOX_DIR="$HOME/.config/openbox"
RULE_FILE="$(dirname "$0")/openbox-monitor-rule.xml"

# Find the Openbox RC file (could be lxde-rc.xml or lubuntu-rc.xml)
RC_FILE=""
if [ -f "$OPENBOX_DIR/lxde-rc.xml" ]; then
    RC_FILE="$OPENBOX_DIR/lxde-rc.xml"
elif [ -f "$OPENBOX_DIR/lubuntu-rc.xml" ]; then
    RC_FILE="$OPENBOX_DIR/lubuntu-rc.xml"
elif [ -f "$OPENBOX_DIR/rc.xml" ]; then
    RC_FILE="$OPENBOX_DIR/rc.xml"
fi

# If no RC file exists, create a minimal one based on the system default
if [ -z "$RC_FILE" ]; then
    echo "No Openbox configuration found. Creating new configuration..."
    mkdir -p "$OPENBOX_DIR"

    # Try to copy from system defaults
    if [ -f "/etc/xdg/openbox/lxde-rc.xml" ]; then
        cp "/etc/xdg/openbox/lxde-rc.xml" "$OPENBOX_DIR/lxde-rc.xml"
        RC_FILE="$OPENBOX_DIR/lxde-rc.xml"
    elif [ -f "/etc/xdg/openbox/lubuntu-rc.xml" ]; then
        cp "/etc/xdg/openbox/lubuntu-rc.xml" "$OPENBOX_DIR/lubuntu-rc.xml"
        RC_FILE="$OPENBOX_DIR/lubuntu-rc.xml"
    elif [ -f "/etc/xdg/openbox/rc.xml" ]; then
        cp "/etc/xdg/openbox/rc.xml" "$OPENBOX_DIR/rc.xml"
        RC_FILE="$OPENBOX_DIR/rc.xml"
    else
        echo "Warning: Could not find system default Openbox configuration."
        echo "Openbox window rule will not be configured."
        exit 0
    fi
fi

echo "Using Openbox configuration: $RC_FILE"

# Check if our rule already exists
if grep -q "Missing Link Status Monitor" "$RC_FILE"; then
    echo "Openbox rule for Status Monitor already exists. Skipping."
    exit 0
fi

# Create backup
cp "$RC_FILE" "$RC_FILE.backup-$(date +%Y%m%d-%H%M%S)"

# Check if <applications> section exists
if ! grep -q "<applications>" "$RC_FILE"; then
    echo "Warning: <applications> section not found in $RC_FILE"
    echo "Cannot add window rule. You may need to add it manually."
    exit 1
fi

# Insert our rule before the closing </applications> tag
RULE_CONTENT=$(cat "$RULE_FILE")
sed -i "/<\/applications>/i\\
$RULE_CONTENT" "$RC_FILE"

echo "Openbox window rule added successfully."
echo "The change will take effect after restarting Openbox or rebooting."
echo "To reload Openbox immediately, run: openbox --reconfigure"
