#!/usr/bin/env bash
# These commands were run to get set up. Run via ./setup.sh

# Make sourcing alias files work in non-interactive shell.
shopt -s expand_aliases

# Run on a Raspberry Pi 3/4/5
# Raspbian GNU/Linux
# Version 12 (bookworm) -- needs to be a recent version.

# Stop the script if any command returns nonzero status.
set -e

# Update
sudo apt-get update

# This include a lot of shortcuts for managing the services running on the pi
cp bash_aliases ~/.bash_aliases
source ~/.bash_aliases

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

# Install and configure dnsmasq dhcp/dns server
dnsmasq.install
dnsmasq.cpconf
dnsmasq.enable
dnsmasq.restart
dnsmasq.status

# Copy /etc/hosts and /etc/hostname
host.cpconf
