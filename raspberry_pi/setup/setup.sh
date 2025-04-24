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

# Copy /etc/hosts and /etc/hostname
cpconf hosts
cpconf hostname

# Install and configure NetworkManager for rpi static ip.
# NM should already be install on latest Raspbian
NetworkManager.status
cpconf wired_connection_1.nmconnection
NetworkManager.restart
NetworkManager.status

# Install and configure mosquitto MQTT broker.
mosquitto.install
cpconf mosquitto.conf
# Set the system to bring up the mosquitto broker.
mosquitto.enable
mosquitto.restart
mosquitto.status

# Install and configure dnsmasq dhcp/dns server
dnsmasq.install
cpconf dnsmasq.conf
# Set it to start up automatically when ethernet is plugged in.
cpconf override.conf
# NOTE: These might fail if ethernet is not plugged in.
# It will succeed when it does -- no need to re-run the script.
dnsmasq.enable
dnsmasq.restart
dnsmasq.status

# Install python dependency manager
wget -qO- https://astral.sh/uv/install.sh | sh
