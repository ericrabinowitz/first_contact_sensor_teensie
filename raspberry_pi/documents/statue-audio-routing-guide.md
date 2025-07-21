# Statue Audio Routing with ADG2188 - Complete Guide

## Project Overview

Multiple interactive statues at Burning Man need to communicate via audio signals. Each statue can transmit and receive audio tones for interaction. The system uses USB audio adapters (CM108-based) connected to Raspberry Pis.

## Problem Description

### Initial Issue
When connecting statue transmitters and receivers:
- When B's transmitter is disconnected: B can detect A's signal
- When B's transmitter is connected (even when muted): Signal detection fails
- Adding a 10kΩ resistor to B's transmitter helps B detect A, but hurts A's ability to hear B

### Root Cause
The CM108 USB audio adapters have mismatched DC bias levels:
- **TX Output**: ~0-1V (near ground)
- **RX Input**: Biased at ~4.4V (for single-supply operation)

When TX and RX are connected, current flows from the high-bias RX (4.4V) to the low TX (~0V), creating a "loading" effect that attenuates signals.

### Additional Complications
- Shared ground between statues creates unwanted signal paths
- AC coupling with bias resistors to ground still allows signal transfer between statues
- Need true isolation between statues when not actively communicating

## Solution: ADG2188 Crosspoint Switch

The ADG2188 is an 8×12 analog crosspoint switch matrix that provides:
- True isolation when switches are open (>1GΩ)
- Low resistance when closed (~300-500Ω at 5V)
- Multiple simultaneous connections possible
- SPI control from Raspberry Pi

## Hardware Setup

### Components Needed
- EVAL-ADG2188EB evaluation board
- 10µF electrolytic capacitors (one per audio connection)
- 5V power supply (or regulator from 12V)
- Jumper wires for Pi connection
- Audio cables with appropriate connectors

### Power Supply Wiring
```
Power Source (choose one):
- 5V from USB
- 5V from Pi pins 2 or 4  
- 12V → 7805 regulator → 5V

EVAL-ADG2188EB Power Connections:
VDD → +5V
VSS → GND (ground)
VL  → 3.3V (from Pi pin 1)
GND → Common Ground (Pi pin 6)
```

### Raspberry Pi SPI Connections
```
Raspberry Pi          EVAL-ADG2188EB
Physical Pin          Signal Name
Pin 19 (GPIO 10)  →   DIN (Data In)
Pin 23 (GPIO 11)  →   SCLK (Serial Clock)
Pin 24 (GPIO 8)   →   CS (Chip Select)
Pin 6             →   GND (Digital Ground)
Pin 1             →   VL (3.3V Logic Supply)
```

### Audio Signal Connections

**Important**: All audio connections need AC coupling capacitors!

```
Inputs (Y pins):
Statue A TX → [10µF cap] → Y0
Statue B TX → [10µF cap] → Y1
Statue C TX → [10µF cap] → Y2
(etc...)

Outputs (X pins):
X0 → [10µF cap] → Statue A RX
X1 → [10µF cap] → Statue B RX
X2 → [10µF cap] → Statue C RX
(etc...)

Capacitor Polarity (for electrolytic):
- Negative (-) side toward TX (lower voltage ~0V)
- Positive (+) side toward switch/RX (higher voltage)
```

## Software Control

### Basic SPI Control (No Libraries)

```python
import RPi.GPIO as GPIO
import time

# Pin definitions
DIN = 10   # GPIO 10 (Physical Pin 19)
SCLK = 11  # GPIO 11 (Physical Pin 23)
CS = 8     # GPIO 8 (Physical Pin 24)

class ADG2188Controller:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DIN, GPIO.OUT)
        GPIO.setup(SCLK, GPIO.OUT)
        GPIO.setup(CS, GPIO.OUT)
        
        # Initial states
        GPIO.output(CS, GPIO.HIGH)
        GPIO.output(SCLK, GPIO.LOW)
        
        # Clear all switches on startup
        self.clear_all()
    
    def write_bit(self, bit):
        """Write a single bit via SPI"""
        GPIO.output(DIN, bit)
        GPIO.output(SCLK, GPIO.HIGH)
        time.sleep(0.000001)  # 1µs
        GPIO.output(SCLK, GPIO.LOW)
        time.sleep(0.000001)
    
    def send_command(self, command):
        """Send 16-bit command to ADG2188"""
        # CS low to start transmission
        GPIO.output(CS, GPIO.LOW)
        time.sleep(0.000001)
        
        # Send 16 bits, MSB first
        for i in range(15, -1, -1):
            bit = (command >> i) & 1
            self.write_bit(bit)
        
        # CS high to latch command
        GPIO.output(CS, GPIO.HIGH)
        time.sleep(0.000001)
    
    def set_switch(self, y_input, x_output, enable):
        """
        Control a single crosspoint
        
        Args:
            y_input: 0-7 (input channel)
            x_output: 0-11 (output channel)
            enable: True to connect, False to disconnect
            
        Command format (16 bits):
        [15:12] = Don't care (0000)
        [11:8]  = Y address
        [7:4]   = X address
        [3:0]   = Data (0001=on, 0000=off)
        """
        command = (y_input << 8) | (x_output << 4) | (1 if enable else 0)
        self.send_command(command)
    
    def clear_all(self):
        """Disconnect all switches"""
        for y in range(8):
            for x in range(12):
                self.set_switch(y, x, False)
    
    def cleanup(self):
        """Clean up GPIO pins"""
        GPIO.cleanup()
```

### High-Level Statue Control

```python
class StatueAudioRouter:
    def __init__(self):
        self.switch = ADG2188Controller()
        self.num_statues = 4  # Adjust based on your setup
    
    def enable_transmission(self, from_statue, to_statue):
        """Enable audio from one statue to another"""
        if from_statue == to_statue:
            return  # Don't create feedback loops
        
        # Map statue IDs to switch pins
        y_pin = from_statue  # TX connects to Y inputs
        x_pin = to_statue    # RX connects to X outputs
        
        self.switch.set_switch(y_pin, x_pin, True)
        print(f"Statue {from_statue} → Statue {to_statue}: ON")
    
    def disable_transmission(self, from_statue, to_statue):
        """Disable audio from one statue to another"""
        y_pin = from_statue
        x_pin = to_statue
        self.switch.set_switch(y_pin, x_pin, False)
        print(f"Statue {from_statue} → Statue {to_statue}: OFF")
    
    def broadcast_mode(self, sender_id):
        """One statue broadcasts to all others"""
        # First clear all connections
        self.switch.clear_all()
        
        # Connect sender to all other statues
        for receiver_id in range(self.num_statues):
            if receiver_id != sender_id:
                self.enable_transmission(sender_id, receiver_id)
    
    def peer_to_peer(self, statue_a, statue_b):
        """Enable bidirectional communication between two statues"""
        # Clear all first
        self.switch.clear_all()
        
        # Enable both directions
        self.enable_transmission(statue_a, statue_b)
        self.enable_transmission(statue_b, statue_a)
    
    def party_mode(self):
        """Everyone can hear everyone"""
        for sender in range(self.num_statues):
            for receiver in range(self.num_statues):
                if sender != receiver:
                    self.enable_transmission(sender, receiver)
    
    def silence_all(self):
        """Disconnect all audio paths"""
        self.switch.clear_all()
        print("All audio paths disconnected")
```

## Usage Examples

```python
# Initialize the router
router = StatueAudioRouter()

# Example 1: Statue 0 broadcasts to all
router.broadcast_mode(0)
time.sleep(5)

# Example 2: Private conversation between statues 1 and 2
router.peer_to_peer(1, 2)
time.sleep(5)

# Example 3: Everyone talks to everyone
router.party_mode()
time.sleep(5)

# Example 4: Silence
router.silence_all()

# Cleanup when done
router.switch.cleanup()
```

## Testing Procedure

### 1. Basic Connectivity Test
```python
def test_basic_connectivity():
    switch = ADG2188Controller()
    
    print("Testing each path individually...")
    for y in range(2):  # Test first 2 inputs
        for x in range(2):  # Test first 2 outputs
            if y != x:  # Avoid feedback
                print(f"\nTesting Y{y} → X{x}")
                switch.set_switch(y, x, True)
                input("Check signal path. Press Enter to continue...")
                switch.set_switch(y, x, False)
    
    switch.cleanup()
```

### 2. Signal Quality Test
1. Generate 1kHz test tone on Statue A
2. Enable path from A to B
3. Measure signal amplitude at B
4. Should see minimal attenuation (<10%)

### 3. Isolation Test
1. Generate different tones on each statue
2. Enable only specific paths
3. Verify only enabled paths pass signal
4. Disabled paths should show >60dB isolation

## Troubleshooting

### No Signal Transfer
- Check power supplies (5V on VDD, 3.3V on VL)
- Verify SPI connections with multimeter
- Check capacitor polarity
- Test with slower SPI clock (increase delays)

### Signal Distortion
- Ensure AC coupling capacitors are properly connected
- Check for proper grounding
- Verify signal levels are within 0-5V range

### Cross-talk Between Channels
- Verify all unused switches are OFF
- Check for ground loops
- Use shielded audio cables for long runs

### SPI Communication Issues
- Add 10kΩ pull-up resistor on CS line
- Check logic levels (3.3V from Pi)
- Verify timing (ADG2188 supports up to 50MHz)

## Design Considerations

### Signal Levels
- Input signals: 0-2V peak-to-peak typical
- Centered around different DC levels (TX: ~0V, RX: ~4V)
- AC coupling removes DC bias differences
- 5V supply provides adequate headroom

### Impedances
- CM108 output impedance: 50-200Ω
- CM108 input impedance: 10-20kΩ  
- ADG2188 on-resistance at 5V: ~500Ω
- Total path resistance: <1kΩ (acceptable for high-Z inputs)

### Burning Man Environmental Factors
- Dust protection: Seal evaluation board in enclosure
- Temperature: ADG2188 rated -40°C to +85°C
- Power: Use regulated supplies, add filtering
- Connectors: Use locking, weatherproof audio connectors

## Alternative Approaches Considered

1. **Direct connection with series resistor**: Too much signal loss
2. **AC coupling only**: Ground paths still caused cross-talk
3. **Separate USB adapters**: Didn't solve voltage mismatch
4. **Op-amp buffers**: More complex than switch matrix
5. **Transformer isolation**: More expensive, bulkier

The ADG2188 provides the cleanest solution with true isolation and flexible routing capabilities.

## Parts List

| Component | Quantity | Notes |
|-----------|----------|-------|
| EVAL-ADG2188EB | 1 | Evaluation board with ADG2188 |
| 10µF capacitor | 8-16 | Electrolytic, 16V minimum |
| Jumper wires | ~10 | Female-female for Pi connection |
| 5V regulator | 1 | 7805 or switching regulator |
| Project box | 1 | Dust-proof enclosure |
| Audio connectors | As needed | 3.5mm or XLR |

## References

- ADG2188 Datasheet: 8×12 Analog Crosspoint Switch
- CM108 USB Audio: Single-supply USB audio codec
- Raspberry Pi GPIO: BCM pin numbering used
- SPI Protocol: Mode 0 (CPOL=0, CPHA=0)