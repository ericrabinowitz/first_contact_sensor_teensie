# Statue Audio Routing Guide (Revised July 2025)

This guide shows how to use the **EVAL‑ADG2188EBZ** 8 × 8 cross‑point switch with a Raspberry Pi to route statue transmit / receive lines cleanly and silently.

> **Major fixes in this revision**\
> • Corrected device to **8 × 8** (not 8 × 12) and **R****ON**** ≈ 30 Ω**\
> • Uses *row‑byte + LDSW* programming (the official method)\
> • Pin labels match the evaluation board (AVDD, AVSS, VL, AGND)\
> • Added AC‑coupling network and bias bleeders\
> • Troubleshooting refers to I²C (not SPI)

---

## Problem Context

Multiple interactive statues need bidirectional audio communication. Direct connection of USB audio adapters (CM108) causes signal loading due to DC bias mismatch:
- TX outputs: ~0V DC bias
- RX inputs: ~4.4V DC bias
- Direct connection causes current flow that attenuates signals

The ADG2188 provides isolated switching to prevent loading when statues aren't actively communicating.

---

## 1 Board power & logic

| ADG2188 pin       | Connect to                             | Notes                   |
| ----------------- | -------------------------------------- | ----------------------- |
| **AVDD** (J4‑1)   | Pi 5 V                                 | 4.5–5.5 V single‑supply |
| **VL** (J4‑3)     | Pi 3 V3                                | Logic‑level reference   |
| **AGND** (J4‑2/4) | Pi GND                                 | Common ground plane     |
| **AVSS**          | **Short to AGND** ( jumper LK4 → *B* ) | Single‑supply mode      |

*Leave the mini‑USB socket empty; the Pi owns the I²C bus.*

---

## 2 I²C wiring

| Pi pin             | EVAL‑ADG2188EBZ  | Default pull‑ups      |
| ------------------ | ---------------- | --------------------- |
| SDA (Pin 3)        | **SDA** (J2‑4)   | 4.7 k Ω → VL on board |
| SCL (Pin 5)        | **SCL** (J2‑5)   | ―                     |
| GPIO 22 (optional) | **LDSW** (J2‑2)  | Latch new settings    |
| GPIO 27 (optional) | **RESET** (J2‑3) | Opens all switches    |

### Jumper Configuration

The EVAL-ADG2188EBZ has 5 jumpers (LK1-LK5) that must be configured:

#### I²C Address Jumpers (LK1, LK2, LK3)
- **Inserted (closed)**: Bit = 0
- **Removed (open)**: Bit = 1
- Default (all inserted): **Address 0x70**
- To change address, remove jumpers (e.g., remove LK1 → 0x71)

#### Power Mode Jumper (LK4)
- **Position A**: Dual supply mode (AVSS connects to external negative supply)
- **Position B**: Single supply mode (AVSS connects to ground) **← Use this**

#### Logic Power Jumper (LK5)
- **Inserted**: Logic power from USB (3.3V from onboard regulator)
- **Removed**: Logic power from external VL pin **← Use this**

### Recommended Configuration for Missing Link

| Jumper | Setting | Purpose |
|--------|---------|---------|
| LK1 | Inserted | I²C address bit A0 = 0 |
| LK2 | Inserted | I²C address bit A1 = 0 |
| LK3 | Inserted | I²C address bit A2 = 0 |
| LK4 | Position B | Single supply mode (5V only) |
| LK5 | Removed | Use Pi's 3.3V for logic |

This gives I²C address **0x70** with single 5V supply and 3.3V logic levels.

### Wiring Diagram

```
         EVAL-ADG2188EBZ
    ┌─────────────────────────┐
    │  Y0 ←─[AC couple]← A TX │
    │  Y1 ←─[AC couple]← B TX │
    │  Y2 ←─[AC couple]← C TX │
    │  Y3 ←─[AC couple]← D TX │
    │                         │
    │  X0 →─[AC couple]→ A RX │
    │  X1 →─[AC couple]→ B RX │
    │  X2 →─[AC couple]→ C RX │
    │  X3 →─[AC couple]→ D RX │
    │                         │
    │  I²C: SDA,SCL ← Pi      │
    │  PWR: 5V,3V3,GND ← Pi   │
    └─────────────────────────┘
```

---

## 3 Audio coupling network (per statue line)

```
Codec OUT ── 100 Ω ─┬─ 1 µF ─► Xn
                   │
                   └─ 1 MΩ ─► GND
```

- 1 µF film (or 4.7 µF bipolar electrolytic) blocks DC.
- 1 MΩ bleed stops floating pickup without loading the codec (< 0.1 dB).
- 100 Ω series resistor protects the driver and damps cable capacitance.

Repeat the same network from Yn back to the opposite statue.

### Capacitor Selection
- **Preferred**: 1µF film or ceramic (non-polarized)
- **Alternative**: 4.7µF bipolar electrolytic
- **If using polarized**: Two 10µF back-to-back
- **Avoid**: Single polarized electrolytic (DC bias varies)

---

## 4 Programming the matrix (row‑byte + LDSW)

Row registers live at **0x74 … 0x7B** (Y0…Y7). Bits 0‑7 represent X0…X7.

```python
import smbus2, time
bus  = smbus2.SMBus(1)   # Pi I²C‑1
addr = 0x70              # JP1 = 000
ROW0 = 0x74              # Y0
LDSW = 0x72

# close X0‑Y0
bus.write_byte_data(addr, ROW0, 0b00000001)
# optional: preload other rows here …

bus.write_byte_data(addr, LDSW, 0x01)   # latch → all selected switches on
```

*Full update latency* = 8 bytes + LDSW ≈ 200 µs @ 400 kHz I²C; switch tON = 170 ns.

### High-Level Control Class

```python
import smbus2
import time

class StatueRouter:
    def __init__(self, bus=1, addr=0x70):
        self.bus = smbus2.SMBus(bus)
        self.addr = addr
        self.ROW_BASE = 0x74
        self.LDSW = 0x72
        self.rows = [0] * 8  # shadow registers

    def connect(self, y_in, x_out):
        """Connect Yn to Xm"""
        self.rows[y_in] |= (1 << x_out)
        self._update()

    def disconnect(self, y_in, x_out):
        """Disconnect Yn from Xm"""
        self.rows[y_in] &= ~(1 << x_out)
        self._update()

    def clear_all(self):
        """Open all switches"""
        self.rows = [0] * 8
        self._update()

    def _update(self):
        """Write all rows then latch"""
        for y, data in enumerate(self.rows):
            self.bus.write_byte_data(self.addr, self.ROW_BASE + y, data)
        self.bus.write_byte_data(self.addr, self.LDSW, 0x01)
```

### Specific Statue Use Cases

```python
# Initialize router
router = StatueRouter()

# Broadcast mode: Statue A to all others
router.connect(0, 1)  # A→B
router.connect(0, 2)  # A→C
router.connect(0, 3)  # A→D

# Peer-to-peer: A↔B only
router.clear_all()
router.connect(0, 1)  # A→B
router.connect(1, 0)  # B→A

# Party mode: Everyone to everyone
for tx in range(4):
    for rx in range(4):
        if tx != rx:  # No self-feedback
            router.connect(tx, rx)
```

---

## 5 LED bench test

1. **Row X0** → LED + 330 Ω → 3 V3.
2. **Col Y0** → LED cathode → GND.
3. Run the Python snippet above.

- LED lights when X0‑Y0 closed, off otherwise – confirms power, I²C, row/col mapping.

---

## 6 Key electrical specs (single‑supply 5 V)

| Parameter     | Typical         | Max  | Source       |
| ------------- | --------------- | ---- | ------------ |
| RON           | 30 Ω            | 35 Ω | DS Table 4   |
| tON/tOFF      | 170 ns / 210 ns | ―    | DS Fig. 18   |
| Off‑isolation | –69 dB @ 5 MHz  | ―    | DS Fig. 25   |
| THD + N       | 0.04 % @ 1 Vpp  | ―    | DS Table 6   |
| Signal swing  | 0 – AVDD        | ―    | Absolute‑max |

DS = ADG2188 datasheet Rev. C.

### Signal Levels
- CM108 output: 0-2Vpp typical (consumer line level)
- ADG2188 handles: 0V to AVDD (5V)
- Headroom: >3V for clean switching
- If clipping occurs: Reduce codec output level in software

---

## 7 Quick Functional Test

1. Power up with no audio connected
2. Run `i2cdetect -y 1` - verify 0x70 appears
3. Connect scope/meter to X0
4. Connect 1kHz test tone to Y0
5. Run: `router.connect(0, 0)`
6. Verify signal passes with <1dB loss
7. Run: `router.disconnect(0, 0)`
8. Verify >60dB isolation

---

## 8 Troubleshooting

| Symptom                        | Check / fix                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------- |
| `i2cdetect` shows **no 0x70**  | Wrong power pins, SDA/SCL swapped, JP1 address ≠ expected                          |
| All switches stay open         | Send `0x72 = 0x01` latch byte; ensure LDSW pin isn't held low                      |
| Pops or stray 10 kHz when idle | Add / verify 1 MΩ bleeder & 1 µF cap; confirm return‑ground path                   |
| High loss (>3 dB)              | Codec driving <5 kΩ due to stray shunts; series resistor too big; measure with DSO |
| Bus errors                     | Slow I²C to 50 kHz; use twisted pair SCL/SDA                                       |

*(Troubleshooting now references I²C only—SPI wording removed.)*

---

## 9 Environmental & enclosure notes

- Chip is rated –40 °C … +85 °C, but cheap CM108 USB dongles are **0 – 70 °C**; keep them shaded.
- Use conformal coating or Gore vents to keep Playa dust out while letting heat escape.
- Secure cables with strain‑relief; RON is low but static can still punch through if grounds detach.

---

© 2025 BM Electronics Art Project.  Based on Analog Devices UG‑915 and ADG2188 Rev. C datasheet.