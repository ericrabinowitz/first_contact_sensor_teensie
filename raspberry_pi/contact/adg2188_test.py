#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["smbus2", "sounddevice"]
# ///

"""Interactive ADG2188 TX switching test.

This script provides an interactive terminal UI for testing TX switching
functionality. It allows real-time control of statue TX connections to
verify the ADG2188 switch matrix is working correctly.

Controls:
- W/S or ↑/↓: Navigate between statues
- Space: Toggle TX connection for selected statue
- E: Enable exclusive mode (only one TX at a time)
- A: Disable all TX connections
- M: Show connection matrix
- Q: Quit
"""

import sys
import termios
import tty
import time
import select
from typing import Optional

from audio.devices import Statue

try:
    from tx_control import TXController
except ImportError:
    # If running standalone, try parent directory
    sys.path.append('..')
    from contact.tx_control import TXController


class InteractiveTXTest:
    """Interactive test UI for TX switching."""

    def __init__(self, simulate: bool = False):
        """Initialize test interface.

        Args:
            simulate: Run in simulation mode without hardware
        """
        self.controller = TXController(simulate=simulate)
        self.running = True
        self.selected_statue = Statue.EROS
        self.show_matrix = False
        self.old_settings = None

    def setup_terminal(self):
        """Set terminal to raw mode for immediate key capture."""
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

    def restore_terminal(self):
        """Restore terminal to normal mode."""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def clear_screen(self):
        """Clear terminal screen."""
        print("\033[2J\033[H", end='', flush=True)

    def draw_ui(self):
        """Draw the interactive UI."""
        self.clear_screen()

        # Header
        print("=== ADG2188 TX Switching Test ===\r\n\r", flush=True)

        # Mode indicators
        mode_str = "[HARDWARE MODE]" if self.controller.hardware_available else "[SIMULATION MODE]"
        excl_str = "[EXCLUSIVE]" if self.controller.exclusive_mode else "[MULTI-TX]"
        print(f"{mode_str} {excl_str}\r\n\r", flush=True)

        # TX Status
        print("TX Connection Status:\r", flush=True)
        print("-" * 30 + "\r", flush=True)

        for statue in Statue:
            enabled = self.controller.is_tx_enabled(statue)
            selected = "→" if statue == self.selected_statue else " "
            status = "■ ON " if enabled else "□ OFF"

            # Highlight selected row
            if statue == self.selected_statue:
                print(f"\033[7m{selected} {statue.value:8s} TX: [{status}]\033[0m\r", flush=True)
            else:
                print(f"{selected} {statue.value:8s} TX: [{status}]\r", flush=True)

        # Show matrix if enabled
        if self.show_matrix and self.controller.hardware_available:
            print("\r\nConnection Matrix:\r", flush=True)
            print("     X0 X1 X2 X3 X4 X5 X6 X7\r", flush=True)
            print("   " + "-" * 28 + "\r", flush=True)

            try:
                matrix = self.controller.switch.get_connections()
                for y, row in enumerate(matrix[:5]):  # Only show Y0-Y4 (statue rows)
                    statue_name = list(self.controller.STATUE_TX_MAP.keys())[y].value[:3].upper()
                    row_str = f"{statue_name} |"
                    for x, connected in enumerate(row):
                        if x == 0:  # Highlight bus column
                            row_str += " ■ " if connected else " · "
                        else:
                            row_str += " · "  # Other columns not used
                    print(row_str + "\r", flush=True)
            except Exception:
                print("[Matrix unavailable]\r", flush=True)

        # Controls
        print("\r\nControls:\r", flush=True)
        print("  W/S or ↑/↓  : Navigate statues\r", flush=True)
        print("  SPACE       : Toggle TX connection\r", flush=True)
        print("  E           : Toggle exclusive mode\r", flush=True)
        print("  A           : All TX off\r", flush=True)
        print("  M           : Show/hide matrix\r", flush=True)
        print("  Q           : Quit\r", flush=True)

        # Status line
        enabled_count = len(self.controller.get_enabled_statues())
        print(f"\r\nActive TX: {enabled_count}/5\r", flush=True)

    def handle_key(self, key: str):
        """Process keyboard input.

        Args:
            key: Single character from keyboard
        """
        if key == 'q' or key == 'Q' or key == '\x1b':  # ESC
            self.running = False

        elif key == 'w' or key == 'W' or key == '\x1b[A':  # Up arrow
            # Move up
            statues = list(Statue)
            idx = statues.index(self.selected_statue)
            if idx > 0:
                self.selected_statue = statues[idx - 1]

        elif key == 's' or key == 'S' or key == '\x1b[B':  # Down arrow
            # Move down
            statues = list(Statue)
            idx = statues.index(self.selected_statue)
            if idx < len(statues) - 1:
                self.selected_statue = statues[idx + 1]

        elif key == ' ':  # Space - toggle TX
            if self.controller.is_tx_enabled(self.selected_statue):
                self.controller.disable_tx(self.selected_statue)
            else:
                self.controller.enable_tx(self.selected_statue)

        elif key == 'e' or key == 'E':  # Toggle exclusive mode
            self.controller.set_exclusive_mode(not self.controller.exclusive_mode)

        elif key == 'a' or key == 'A':  # All off
            self.controller.disable_all_tx()

        elif key == 'm' or key == 'M':  # Toggle matrix display
            self.show_matrix = not self.show_matrix

    def read_key(self) -> Optional[str]:
        """Read a key with support for arrow keys.

        Returns:
            Key character or None if no input
        """
        if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
            key = sys.stdin.read(1)

            # Check for escape sequences (arrow keys)
            if key == '\x1b':
                if sys.stdin in select.select([sys.stdin], [], [], 0.01)[0]:
                    key += sys.stdin.read(1)
                    if key[-1] == '[':
                        if sys.stdin in select.select([sys.stdin], [], [], 0.01)[0]:
                            key += sys.stdin.read(1)

            return key
        return None

    def run(self):
        """Run the interactive test loop."""
        self.setup_terminal()

        try:
            # Hide cursor
            print("\033[?25l", end='', flush=True)

            while self.running:
                self.draw_ui()

                # Check for keyboard input
                key = self.read_key()
                if key:
                    self.handle_key(key)

                time.sleep(0.05)  # Small delay to reduce CPU usage

        except KeyboardInterrupt:
            pass
        finally:
            # Show cursor
            print("\033[?25h", end='', flush=True)
            self.restore_terminal()
            self.clear_screen()
            print("Test complete.\n")


def main():
    """Run the interactive TX test."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive test for ADG2188 TX switching"
    )
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='Run in simulation mode without hardware'
    )

    args = parser.parse_args()

    print("Starting ADG2188 TX switching test...")
    print("Initializing controller...")

    test = InteractiveTXTest(simulate=args.simulate)

    if not args.simulate and not test.controller.hardware_available:
        print("\nWARNING: Hardware not detected, running in simulation mode")
        print("Make sure:")
        print("- I2C is enabled (raspi-config)")
        print("- ADG2188 is powered and connected")
        print("- smbus2 is installed")
        input("\nPress Enter to continue in simulation mode...")

    test.run()


if __name__ == "__main__":
    main()