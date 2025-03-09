alias aliases="vim ~/.bash_aliases && source ~/.bashrc"
alias status="sudo systemctl --no-pager --lines=0 status NetworkManager mosquitto dnsmasq"
alias restart="sudo systemctl restart NetworkManager.service mosquitto.service dnsmasq.service"
alias leases="cat /var/lib/misc/dnsmasq.leases"
alias arp.local="arp -a | grep 192.168.4.1"

# Aliases for dnsmasq
alias dnsmasq.conf="sudo vim /etc/dnsmasq.conf"
alias dnsmasq.restart="sudo systemctl restart dnsmasq.service"
alias dnsmasq.status="sudo systemctl status dnsmasq.service"
alias dnsmasq.logs="journalctl -eu dnsmasq"

# Aliases for NetworkManager
alias NetworkManager.conf="sudo vim /etc/NetworkManager/system-connections/wired_connection_1"
alias NetworkManager.restart="sudo systemctl restart NetworkManager.service"
alias NetworkManager.status="sudo systemctl status NetworkManager.service"
alias NetworkManager.logs="journalctl -eu NetworkManager"

# Aliases for NetworkManager
alias mosquitto.conf="sudo vim /etc/mosquitto/mosquitto.conf"
alias mosquitto.restart="sudo systemctl restart mosquitto.service"
alias mosquitto.status="sudo systemctl status mosquitto.service"
alias mosquitto.logs="journalctl -eu mosquitto.service"
