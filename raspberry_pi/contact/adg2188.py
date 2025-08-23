#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["smbus2"]
# ///

"""ADG2188 8x8 Analog Switch Matrix Control

This module provides low-level control of the ADG2188 analog crosspoint switch
via I2C interface. The ADG2188 is used to route audio signals between statues
while preventing signal loading issues.

The switch matrix uses row-byte + LDSW programming:
- Y inputs (rows): Connect to statue TX outputs
- X outputs (columns): Connect to routing destinations
- Row registers at 0x74-0x7B control Y0-Y7
- Each bit in a row register connects to corresponding X output
- LDSW register at 0x72 latches the configuration
"""

import smbus2
from typing import Optional


class ADG2188:
    """Control ADG2188 8x8 analog switch matrix via I2C."""
    
    # Register addresses from datasheet
    ROW_BASE = 0x74  # Y0 register (0x74-0x7B for Y0-Y7)
    LDSW = 0x72      # Load switch register to latch configuration
    
    def __init__(self, bus: int = 1, address: int = 0x70):
        """Initialize ADG2188 controller.
        
        Args:
            bus: I2C bus number (1 for Pi I2C-1)
            address: I2C address (0x70 default with JP1=000)
        """
        self.bus = smbus2.SMBus(bus)
        self.address = address
        self.rows = [0] * 8  # Shadow registers for Y0-Y7
        self.clear_all()
        
    def connect(self, y_in: int, x_out: int) -> bool:
        """Connect Y[y_in] input to X[x_out] output.
        
        Args:
            y_in: Y input pin (0-7)
            x_out: X output pin (0-7)
            
        Returns:
            True if successful, False if invalid pins
        """
        if 0 <= y_in < 8 and 0 <= x_out < 8:
            self.rows[y_in] |= (1 << x_out)
            self._update()
            return True
        return False
    
    def disconnect(self, y_in: int, x_out: int) -> bool:
        """Disconnect Y[y_in] from X[x_out].
        
        Args:
            y_in: Y input pin (0-7)
            x_out: X output pin (0-7)
            
        Returns:
            True if successful, False if invalid pins
        """
        if 0 <= y_in < 8 and 0 <= x_out < 8:
            self.rows[y_in] &= ~(1 << x_out)
            self._update()
            return True
        return False
    
    def set_row(self, y_in: int, connections: int) -> bool:
        """Set all connections for a Y row at once.
        
        Args:
            y_in: Y input pin (0-7)
            connections: 8-bit mask of X connections
            
        Returns:
            True if successful, False if invalid pin
        """
        if 0 <= y_in < 8:
            self.rows[y_in] = connections & 0xFF
            self._update()
            return True
        return False
    
    def get_row(self, y_in: int) -> Optional[int]:
        """Get current connections for a Y row.
        
        Args:
            y_in: Y input pin (0-7)
            
        Returns:
            8-bit mask of X connections, or None if invalid
        """
        if 0 <= y_in < 8:
            return self.rows[y_in]
        return None
    
    def clear_all(self):
        """Open all switches."""
        self.rows = [0] * 8
        self._update()
    
    def _update(self):
        """Write shadow registers to device and latch configuration."""
        try:
            # Write all row registers
            for y, data in enumerate(self.rows):
                self.bus.write_byte_data(
                    self.address, 
                    self.ROW_BASE + y, 
                    data
                )
            # Latch the new configuration
            self.bus.write_byte_data(self.address, self.LDSW, 0x01)
        except Exception as e:
            print(f"ADG2188 I2C error: {e}")
            raise
    
    def get_connections(self) -> list[list[bool]]:
        """Return current connection matrix.
        
        Returns:
            8x8 matrix where [y][x] is True if connected
        """
        matrix = []
        for y in range(8):
            row = []
            for x in range(8):
                connected = bool(self.rows[y] & (1 << x))
                row.append(connected)
            matrix.append(row)
        return matrix
    
    def print_matrix(self):
        """Print connection matrix for debugging."""
        print("ADG2188 Connection Matrix:")
        print("     X0 X1 X2 X3 X4 X5 X6 X7")
        print("   " + "-" * 28)
        
        matrix = self.get_connections()
        for y, row in enumerate(matrix):
            row_str = f"Y{y} |"
            for x, connected in enumerate(row):
                row_str += " ■ " if connected else " · "
            print(row_str)
    
    def verify_communication(self) -> bool:
        """Verify I2C communication with device.
        
        Returns:
            True if device responds correctly
        """
        try:
            # Try to read back a row register
            data = self.bus.read_byte_data(self.address, self.ROW_BASE)
            return True
        except Exception:
            return False


def main():
    """Test ADG2188 basic functionality."""
    print("ADG2188 Basic Test")
    print("-" * 40)
    
    try:
        switch = ADG2188()
        
        if switch.verify_communication():
            print("✓ I2C communication verified")
        else:
            print("✗ I2C communication failed")
            return
        
        # Test connections
        print("\nTest 1: Connect Y0 to X0")
        switch.connect(0, 0)
        switch.print_matrix()
        
        print("\nTest 2: Connect Y1 to multiple outputs")
        switch.connect(1, 1)
        switch.connect(1, 2)
        switch.connect(1, 3)
        switch.print_matrix()
        
        print("\nTest 3: Clear all")
        switch.clear_all()
        switch.print_matrix()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("- I2C is enabled on the Pi")
        print("- ADG2188 is powered and connected")
        print("- I2C address is correct (default 0x70)")


if __name__ == "__main__":
    main()