# Missing Link

The art project involves 2 or more life sized statues. When a human chain is formed between statue pairs, those statues should light up and start playing music.

## Electronics

Teensy 4.1 with Audio Shield and Ethernet breakout board
Raspberry Pi 3B+ or 4B
QuinLED-Dig-Octa Brainboard-32-8L
Switch
LED strings
Haptic motors
Speakers
Power systems
Optional WiFi router

## Software

Raspberry Pi

- DHCP server
- DNS resolver
- MQTT broker
- New: Controller script: plays audio, sends motor cmds to Teensy and sends WLED cmds.

Teensy

- Controller script detects touches, plays audio, sends WLED cmds.

QuinLED board

- Runs WLED software, which drives light effects.

## Software TODOs

- Update Teensy to sends mqtt msgs on link and unlink.
- Update Teensy to receive motor cmds over mqtt.
- Update Teensy to support auto-provisioning. Mainly, which Teensy maps to which statue.
- Figure out how audio should play across multiple statue contact pairings.
- Turn off lights during the day.
- etc
