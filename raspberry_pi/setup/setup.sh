#!/usr/bin/env bash

# This script sets up the Raspberry Pi.
# Execute: ./setup.sh
# Supports:
#   Raspberry Pi 3/4/5
#   Raspbian GNU/Linux
#   based on Debian 12 (bookworm) -- needs to be a recent version.

# Make sourcing alias files work in non-interactive shell.
shopt -s expand_aliases

# Stop the script if any command returns nonzero status.
set -e

# Update
sudo apt update

# This include a lot of shortcuts for managing the services running on the pi
cp bash_aliases ~/.bash_aliases
source ~/.bash_aliases

# Copy /etc/hosts and /etc/hostname
host.cpconf

# Install and configure NetworkManager for rpi static ip.
# NM should already be install on latest Raspbian
NetworkManager.status
NetworkManager.cpconf
NetworkManager.restart
NetworkManager.status

# Install and configure mosquitto MQTT broker.
mosquitto.install
mosquitto.cpconf
# Set the system to bring up the mosquitto broker.
mosquitto.enable
mosquitto.restart
mosquitto.status

# Install and configure the controller program.
controller.install
controller.cpconf
# Set the system to bring up the controller.
controller.enable
controller.restart
controller.status

tools.install

# Add additional commands above this line. Script might fail after
# attempting to start dnsmasq.

# Install and configure dnsmasq dhcp/dns server
# Set it to start up automatically when ethernet is plugged in.
dnsmasq.install
dnsmasq.cpconf
# NOTE: These might fail if ethernet is not plugged in.
# It will succeed when it does -- no need to re-run the script.
dnsmasq.enable
dnsmasq.restart
dnsmasq.status
