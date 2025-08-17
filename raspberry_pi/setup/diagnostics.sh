#!/usr/bin/env bash

# This script runs diagnostic commands across all of the devices.
# Execute: ./diagnostics.sh

set -euo pipefail

printf "\nRunning diagnostics...\n"

printf "\nBasic Linux stats\n"
echo "OS details:"
uname -a
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo "Uptime:"
uptime
echo "Free memory:"
free -h
echo "Disk usage:"
df -h
echo "CPU and I/O stats:"
iostat
echo "CPU Temperature:"
vcgencmd measure_temp
sleep 3

printf "\nNetwork configuration:\n"
echo "Interfaces:"
ip -br a
echo "ARP table:"
arp -a | grep 192.168.4.
echo "DNSMasq leases:"
sudo cat /var/lib/misc/dnsmasq.leases

sleep 3

printf "\nService statuses:\n"
echo "NetworkManager:"
sudo systemctl status --no-pager NetworkManager | grep -i active
echo "dnsmasq:"
sudo systemctl status --no-pager dnsmasq | grep -i active
echo "mosquitto:"
sudo systemctl status --no-pager mosquitto | grep -i active
echo "controller:"
sudo systemctl status --no-pager controller | grep -i active

sleep 3

printf "\nPing WLED boards:\n"
echo "five_v_1:"
ping -c 2 192.168.4.11 | grep "packet loss"
echo "five_v_2:"
ping -c 2 192.168.4.12 | grep "packet loss"
echo "twelve_v_1:"
ping -c 2 192.168.4.13 | grep "packet loss"

printf "\nPing Teensy controllers:\n"
echo "elektra:"
ping -c 2 192.168.4.23 | grep "packet loss"
echo "ariel:"
ping -c 2 192.168.4.24 | grep "packet loss"
echo "sophia:"
ping -c 2 192.168.4.25 | grep "packet loss"
echo "eros:"
ping -c 2 192.168.4.26 | grep "packet loss"
echo "ultimo:"
ping -c 2 192.168.4.27 | grep "packet loss"

printf "\nController basic stats:\n"
curl http://127.0.0.1:8080/info

printf "\nController current status:\n"
curl http://192.168.4.1:8080/config/dynamic

sleep 3

printf "\nStop the controller and test the audio:\n"
sudo systemctl stop controller
device=$(python3 -m sounddevice | grep -i "hifiberry" | grep -o 'hw:[0-9],[0-9]')
for i in {1..8}; do
    echo ""
    echo "Testing audio output $i..."
    # https://manpages.debian.org/testing/alsa-utils/speaker-test.1.en.html
    speaker-test -D "plug$device" -c 8 -f 440 -p 3000000 -s "$i"
done

printf "\nTest WLED cmds:\n"
echo "All lights on:"
mosquitto_pub -t "wled/all/api" -m '{"on":"t", "bri":255, "tt":0}'
sleep 3
mosquitto_pub -t "wled/all/api" -m '{"on":"t", "bri":0, "tt":0}'

echo "eros on:"
# mosquitto_pub -t "wled/five_v_1/api" -m '{"on":"t", "bri":255, "tt":0}'
# sleep 3
# mosquitto_pub -t "wled/five_v_1/api" -m '{"on":"t", "bri":0, "tt":0}'

printf "\nStart controller and simulate a series of touches:\n"
sudo systemctl start controller
echo "Wait 7 seconds for the controller to start..."
sleep 7
echo "Don't touch the statues for 12 seconds..."

echo "eros -> elektra"
mosquitto_pub -t "missing_link/contact" -m '{"detector":"eros", "emitters":["elektra"]}'
sleep 3
mosquitto_pub -t "missing_link/contact" -m '{"detector":"eros", "emitters":[]}'

echo "ariel -> sophia"
mosquitto_pub -t "missing_link/contact" -m '{"detector":"ariel", "emitters":["sophia"]}'
sleep 3
mosquitto_pub -t "missing_link/contact" -m '{"detector":"ariel", "emitters":[]}'

echo "elektra -> ultimo"
mosquitto_pub -t "missing_link/contact" -m '{"detector":"elektra", "emitters":["ultimo"]}'
sleep 3
mosquitto_pub -t "missing_link/contact" -m '{"detector":"elektra", "emitters":[]}'

echo "ultimo -> eros, elektra, ariel, sophia"
mosquitto_pub -t "missing_link/contact" -m '{"detector":"ultimo", "emitters":["eros", "elektra", "ariel", "sophia"]}'
sleep 3
mosquitto_pub -t "missing_link/contact" -m '{"detector":"ultimo", "emitters":[]}'
