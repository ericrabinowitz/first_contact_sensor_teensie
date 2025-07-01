"""Link state tracking for statue connections.

This module provides the LinkStateTracker class which monitors
connection states between statues and manages audio channel activation.
"""

import sys
sys.path.append('../')

from audio.devices import Statue


class LinkStateTracker:
    """Tracks link states between statues and detects changes."""

    def __init__(self, playback=None, quiet=False):
        # Track which statues are linked to which
        self.links = {}  # {statue: set(linked_statues)}
        # Track link state for each statue (any links at all)
        self.has_links = {}  # {statue: bool}
        # Initialize all statues as unlinked
        for statue in Statue:
            self.links[statue] = set()
            self.has_links[statue] = False
        # Audio playback controller
        self.playback = playback
        # Map statue to channel index using enum order
        self.statue_to_channel = {statue: list(Statue).index(statue) for statue in Statue}
        # Quiet mode suppresses print statements
        self.quiet = quiet

    def _update_audio_channel(self, statue, is_linked):
        """Helper to update audio channel based on link state."""
        if self.playback and statue in self.statue_to_channel:
            channel = self.statue_to_channel[statue]
            if is_linked and not self.playback.channel_enabled[channel]:
                # Turn on channel
                self.playback.toggle_channel(channel)
                if not self.quiet:
                    print(f"  ♪ Audio channel {channel} ON for {statue.value}")
            elif not is_linked and self.playback.channel_enabled[channel]:
                # Turn off channel
                self.playback.toggle_channel(channel)
                if not self.quiet:
                    print(f"  ♪ Audio channel {channel} OFF for {statue.value}")

    def update_link(self, detector_statue, source_statue, is_linked):
        """
        Update link state and return True if state changed.
        Links are bidirectional.
        """
        changed = False

        if is_linked:
            # Add link if not already present
            if source_statue not in self.links[detector_statue]:
                self.links[detector_statue].add(source_statue)
                self.links[source_statue].add(detector_statue)
                changed = True
                if not self.quiet:
                    print(f"🔗 Link established: {detector_statue.value} ↔ {source_statue.value}")
        else:
            # Remove link if present
            if source_statue in self.links[detector_statue]:
                self.links[detector_statue].remove(source_statue)
                self.links[source_statue].remove(detector_statue)
                changed = True
                if not self.quiet:
                    print(f"🔌 Link broken: {detector_statue.value} ↔ {source_statue.value}")

        # Update has_links status
        old_has_links_detector = self.has_links[detector_statue]
        old_has_links_source = self.has_links[source_statue]

        self.has_links[detector_statue] = len(self.links[detector_statue]) > 0
        self.has_links[source_statue] = len(self.links[source_statue]) > 0

        # Check if overall link status changed
        if old_has_links_detector != self.has_links[detector_statue]:
            status = "linked" if self.has_links[detector_statue] else "unlinked"
            if not self.quiet:
                print(f"  → {detector_statue.value} is now {status}")
            changed = True
            # Update audio channel
            self._update_audio_channel(detector_statue, self.has_links[detector_statue])

        if old_has_links_source != self.has_links[source_statue]:
            status = "linked" if self.has_links[source_statue] else "unlinked"
            if not self.quiet:
                print(f"  → {source_statue.value} is now {status}")
            changed = True
            # Update audio channel
            self._update_audio_channel(source_statue, self.has_links[source_statue])

        return changed

    def get_link_summary(self):
        """Return human-readable link summary."""
        summary = []
        summary.append("=== Current Link Status ===")

        # Show linked statues
        linked = [s for s in Statue if self.has_links[s]]
        unlinked = [s for s in Statue if not self.has_links[s]]

        if linked:
            summary.append("Linked statues:")
            for statue in linked:
                linked_to = ", ".join([s.value for s in self.links[statue]])
                summary.append(f"  {statue.value} ↔ {linked_to}")

        if unlinked:
            summary.append("Unlinked statues:")
            summary.append("  " + ", ".join([s.value for s in unlinked]))

        return "\n".join(summary)