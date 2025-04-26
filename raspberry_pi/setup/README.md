README

This directory includes configurations and installation for setting up the raspberry pi server.

To install, run from within the setup directory: `bash setup.sh`

A working image that can be flashed is also available at https://www.dropbox.com/scl/fi/znpy3l43pblnhp0es6y9i/rpi_server.tgz?rlkey=r8cva44kwib85w6e607yqzol5&st=vzqh2c9j&dl=0
TODO: test the image

The server acts as dhcp server, dns server, and mqtt broker for the other nodes in the network over ethernet. There are 3 services that accomplish this:

- dnsmasq acts as both the dhcp server and dns services
- NetworkManager configure the local pi's network setup such as its static ip and dns.
- mosquitto acts as the mqtt broker used for lightweight communication with other nodes.

This setup directory includes:
bash_aliases:

- Command aliases to aid in installation and management of services.
- Notable aliases
  - arp.local: returns local hosts and IPs.
  - <service>. for service in dnsmasq, NetworkManager, mosquitto
    - status, logs, stop, restart, disable, enable
  - <service>.cpconf can be run from within the setup dir to copy configuration to the correct location.

setup.sh:
Setup involves installing, configuring, and checking the status of 3 services Configuration:

- dnsmasq.conf: The dnsmasq config.
- mosquitto.conf: The mosquitto broker config.
- wired_connection_1: The NetworkManager ethernet profile.
- hostname: Sets the hostname of the rpi server to rpi.
- hosts: Sets some static DNS records especially the rpi server alias of rpi_server.
