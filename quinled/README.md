# WLED Configuration

Use the following website to flash the QuinLED Esp32 board:

- https://install.quinled.info/dig-octa/

Connect to the WLED-AP WiFi network.

Go to Config >> Sync Interfaces >> MQTT

- Check Enable MQTT
- Set the Broker to 192.168.4.1
- Set the Device Topic to wled/[statue name]
- Disable the Philips Hue integration

Go to Config >> LED Preferences. For each LED output:

- Confirm that the LED # is 1 greater than the GPIO #. The LED #
  should correspond to the IO port # on the board. See the pinout
  here: https://quinled.info/quinled-dig-octa-brainboard-32-8l-pinout-guide/
- For LEDs:
  - Set the type to WS281x
  - Set the Length to the number of the LEDs in that string.
  - Set the Color Order to either GRB or RGB.
- For the haptic motor (no longer used):
  - Set the type to PWM White
  - Set the Length to 1
- Remember the starting index of each LED output, useful when defining segments.

Go to Segments (bottom row)

- For now we are using the default segment (id=0), that contains all of the LEDs.

## Reference

https://quinled.info/quinled-dig-octa-brainboard-32-8l-pinout-guide/
