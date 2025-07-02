"""Link state tracking for statue connections.

This module provides the LinkStateTracker class which monitors connection
states between statues and manages audio channel activation. It serves as
the bridge between the contact detection system and the audio playback system.

Key Concepts:
- Links are bidirectional: If A detects B, then B also detects A
- Each statue can be linked to multiple other statues simultaneously
- Audio channels are activated when a statue has ANY active links
- The system maintains both detailed link information and summary states

State Management:
- links: Detailed tracking of which statues are connected to which
- has_links: Simple boolean state for audio channel control
- Audio channels toggle automatically based on link state changes

Example:
    >>> tracker = LinkStateTracker(playback_controller)
    >>> tracker.update_link(Statue.EROS, Statue.ELEKTRA, True)
    🔗 Link established: eros ↔ elektra
      → eros is now linked
      ♪ Audio channel 0 ON for eros
      → elektra is now linked
      ♪ Audio channel 1 ON for elektra
"""

import sys
from typing import TYPE_CHECKING, Optional

sys.path.append('../')

from audio.devices import Statue

if TYPE_CHECKING:
    from audio.music import ToggleableMultiChannelPlayback


class LinkStateTracker:
    """Tracks link states between statues and manages audio activation.

    This class maintains the connection graph between statues and automatically
    controls audio playback channels based on link states. When any statue
    becomes linked (has at least one connection), its audio channel is enabled.

    The tracker ensures consistency by:
    - Maintaining bidirectional links (A→B implies B→A)
    - Updating audio channels atomically with link changes
    - Providing both detailed and summary views of connection state

    Attributes:
        links (dict): Maps each statue to set of connected statues
        has_links (dict): Quick lookup for whether statue has any links
        playback: Optional ToggleableMultiChannelPlayback instance
        statue_to_channel (dict): Maps statue to audio channel index
        quiet (bool): Suppress console output when True
    """

    def __init__(self, playback: Optional['ToggleableMultiChannelPlayback'] = None, quiet: bool = False) -> None:
        """Initialize link state tracker.

        Args:
            playback (ToggleableMultiChannelPlayback, optional): Audio controller
                for automatic channel management. If None, only tracks state.
            quiet (bool): Suppress console output for silent operation
        """
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

    def _update_audio_channel(self, statue: Statue, is_linked: bool) -> None:
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

    def update_link(self, detector_statue: Statue, source_statue: Statue, is_linked: bool) -> bool:
        """Update link state between two statues.

        This is the main entry point for the detection system. When a statue
        detects (or stops detecting) another statue's tone, this method updates
        the connection graph and manages audio channels.

        The method ensures bidirectional consistency: if EROS detects ELEKTRA,
        then ELEKTRA is also marked as detecting EROS. This reflects the
        physical reality of the installation where connections are symmetric.

        Args:
            detector_statue (Statue): The statue that detected the tone
            source_statue (Statue): The statue whose tone was detected
            is_linked (bool): True if tone detected, False if lost

        Returns:
            bool: True if any state changed, False if no change

        Side Effects:
            - Updates internal link graph
            - May toggle audio channels via playback controller
            - Prints status messages (unless quiet=True)
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

    def get_link_summary(self) -> str:
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
