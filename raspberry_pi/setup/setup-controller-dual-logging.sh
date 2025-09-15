#!/bin/bash

echo "Setting up dual logging for controller service..."

# Create log directory
sudo mkdir -p /var/log/missing-link
sudo chown pi:pi /var/log/missing-link

# Create systemd override (keeps original service intact)
sudo mkdir -p /etc/systemd/system/controller.service.d
sudo tee /etc/systemd/system/controller.service.d/logging.conf > /dev/null << 'CONFIG'
[Service]
# Log to both journal AND file
ExecStart=
ExecStart=/bin/bash -c '/home/pi/first_contact_sensor_teensie/raspberry_pi/controller/controller.py 2>&1 | tee -a /var/log/missing-link/controller.log'
CONFIG

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart controller

echo ""
echo "✓ Controller dual logging configured!"
echo ""
echo "Logs are now saved to both:"
echo "  1. Journal (view with: controller.logs)"
echo "  2. File (view with: tail -f /var/log/missing-link/controller.log)"
echo ""
echo "Useful commands:"
echo "  tail -f /var/log/missing-link/controller.log    # Follow live"
echo "  tail -n 100 /var/log/missing-link/controller.log # Last 100 lines"
echo "  grep 'dormant' /var/log/missing-link/controller.log"