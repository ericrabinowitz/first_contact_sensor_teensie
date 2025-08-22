#!/usr/bin/env python3
"""TX switching control for statue audio routing.

This module provides high-level control for managing transmitter connections
to prevent signal loading in the Missing Link installation. It wraps the
ADG2188 switch matrix to provide statue-specific TX enable/disable functionality.

Key features:
- Maps statue names to switch matrix pins
- Provides simulation mode for testing without hardware
- Tracks TX connection states
- Ensures only one TX can be connected at a time (optional)
"""

from typing import Optional

from audio.devices import Statue

try:
    from .adg2188 import ADG2188
    HAS_ADG2188 = True
except ImportError:
    HAS_ADG2188 = False
    print("ADG2188 module not available - TX control will run in simulation mode")


class TXController:
    """Manage TX connections to prevent signal loading."""
    
    # Map statues to Y inputs (TX connections)
    STATUE_TX_MAP = {
        Statue.EROS: 0,     # Y0
        Statue.ELEKTRA: 1,  # Y1
        Statue.SOPHIA: 2,   # Y2
        Statue.ULTIMO: 3,   # Y3
        Statue.ARIEL: 4,    # Y4
    }
    
    BUS_X_PIN = 0  # X0 is common bus output
    
    def __init__(self, simulate: bool = False, exclusive_mode: bool = False):
        """Initialize TX controller.
        
        Args:
            simulate: If True, simulate switch operations without hardware
            exclusive_mode: If True, only one TX can be enabled at a time
        """
        self.simulate = simulate
        self.exclusive_mode = exclusive_mode
        self.hardware_available = False
        
        if not simulate and HAS_ADG2188:
            try:
                self.switch = ADG2188()
                if self.switch.verify_communication():
                    self.hardware_available = True
                    print("ADG2188 hardware initialized successfully")
                else:
                    print("ADG2188 communication failed - running in simulation mode")
                    self.simulate = True
            except Exception as e:
                print(f"ADG2188 hardware not available: {e}")
                print("Running in simulation mode")
                self.simulate = True
        else:
            self.simulate = True
            
        # Track TX states
        self.tx_states = {statue: False for statue in Statue}
        
        # Initialize with all TX disconnected
        if self.hardware_available:
            self.switch.clear_all()
        
    def enable_tx(self, statue: Statue) -> bool:
        """Connect statue TX to bus.
        
        Args:
            statue: Statue to enable TX for
            
        Returns:
            True if successful
        """
        y_pin = self.STATUE_TX_MAP.get(statue)
        if y_pin is None:
            print(f"Unknown statue: {statue}")
            return False
        
        # In exclusive mode, disable all other TX first
        if self.exclusive_mode:
            for other_statue in Statue:
                if other_statue != statue and self.tx_states[other_statue]:
                    self.disable_tx(other_statue)
        
        if self.simulate:
            self.tx_states[statue] = True
            print(f"[SIM] TX enabled: {statue.value}")
            return True
        else:
            try:
                success = self.switch.connect(y_pin, self.BUS_X_PIN)
                if success:
                    self.tx_states[statue] = True
                    print(f"TX enabled: {statue.value}")
                return success
            except Exception as e:
                print(f"Failed to enable TX for {statue.value}: {e}")
                return False
    
    def disable_tx(self, statue: Statue) -> bool:
        """Disconnect statue TX from bus.
        
        Args:
            statue: Statue to disable TX for
            
        Returns:
            True if successful
        """
        y_pin = self.STATUE_TX_MAP.get(statue)
        if y_pin is None:
            print(f"Unknown statue: {statue}")
            return False
            
        if self.simulate:
            self.tx_states[statue] = False
            print(f"[SIM] TX disabled: {statue.value}")
            return True
        else:
            try:
                success = self.switch.disconnect(y_pin, self.BUS_X_PIN)
                if success:
                    self.tx_states[statue] = False
                    print(f"TX disabled: {statue.value}")
                return success
            except Exception as e:
                print(f"Failed to disable TX for {statue.value}: {e}")
                return False
    
    def is_tx_enabled(self, statue: Statue) -> bool:
        """Check if statue TX is connected.
        
        Args:
            statue: Statue to check
            
        Returns:
            True if TX is enabled
        """
        return self.tx_states.get(statue, False)
    
    def disable_all_tx(self):
        """Disconnect all TX from bus."""
        for statue in Statue:
            if self.tx_states[statue]:
                self.disable_tx(statue)
    
    def get_enabled_statues(self) -> list[Statue]:
        """Get list of statues with TX enabled.
        
        Returns:
            List of statues with TX currently enabled
        """
        return [statue for statue, enabled in self.tx_states.items() if enabled]
    
    def print_status(self):
        """Print current TX connection status."""
        print("TX Connection Status:")
        print("-" * 30)
        for statue in Statue:
            status = "ON " if self.tx_states[statue] else "OFF"
            print(f"{statue.value:8s} TX: [{status}]")
        
        if self.simulate:
            print("\n[SIMULATION MODE]")
        elif self.hardware_available:
            print("\n[HARDWARE MODE]")
    
    def set_exclusive_mode(self, exclusive: bool):
        """Set whether only one TX can be enabled at a time.
        
        Args:
            exclusive: If True, enabling a TX disables all others
        """
        self.exclusive_mode = exclusive
        if exclusive and len(self.get_enabled_statues()) > 1:
            print("Multiple TX enabled - disabling all but first")
            enabled = self.get_enabled_statues()
            for statue in enabled[1:]:
                self.disable_tx(statue)


def main():
    """Test TX controller functionality."""
    import time
    
    print("TX Controller Test")
    print("=" * 40)
    
    # Test in simulation mode first
    print("\n1. Testing in simulation mode:")
    controller = TXController(simulate=True)
    
    # Enable some TX
    controller.enable_tx(Statue.EROS)
    controller.enable_tx(Statue.ELEKTRA)
    controller.print_status()
    
    # Test exclusive mode
    print("\n2. Testing exclusive mode:")
    controller.set_exclusive_mode(True)
    controller.enable_tx(Statue.SOPHIA)  # Should disable others
    controller.print_status()
    
    # Test disable all
    print("\n3. Testing disable all:")
    controller.disable_all_tx()
    controller.print_status()
    
    # Try hardware mode
    print("\n4. Attempting hardware mode:")
    hw_controller = TXController(simulate=False)
    if hw_controller.hardware_available:
        print("Hardware detected - running quick test")
        hw_controller.enable_tx(Statue.EROS)
        time.sleep(1)
        hw_controller.disable_tx(Statue.EROS)
    else:
        print("No hardware available")


if __name__ == "__main__":
    main()