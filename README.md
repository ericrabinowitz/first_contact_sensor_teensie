# first_contact_sensor_teensie

The project involves 2 or more life sized statues. When a human chain is formed between statue pairs, those statues should light up and start playing music. 

## Hardware
Teensy 4.1 with Audio Shield and Ethrenet breakout board
Raspberry Pi 3B+ or 4B
QuinLED-Dig-Octa Brainboard-32-8L

## Software
Raspberry Pi
- DHCP server
- DNS resolver
- MQTT broker

Teensy
- Controller script detects touches, plays audio, sends WLED cmds.

QuinLED board
- Runs WLED software, which manages the haptic motor and all the LEDs.
