# first_contact_sensor_teensie

Teensy_Sensor - Sketch for Teensy 4.02
This will be the primary application running for the connection sensor.
It contains

- Tone Emission
- Tone Detect
- Tone Detection Reporting via TCP/IP

LinkStatus - This is a demonstration of Ethernet using QNEthernet Library by Shawn Silverman
Dial Tone Serial - Demonstration of Tone Emission and Detection based on the original Teensy Example demo
Note this has been enhanced for a full alphabet of keys, emits 3 tones simultaneously and patches line out to line in + emits via the 3.5mm jack.

## Flash a Teensy board

First connect the Teensy board to the Pi via USB. Then on the Pi, run

```bash
teensy_loader_cli --mcu=TEENSY41 -w FirstContact_controller.hex
```

## Reference

https://www.pjrc.com/teensy/tutorial.html
