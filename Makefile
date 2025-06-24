# Missing Link Project Makefile
# Commands for managing the Missing Link art installation

# Default SSH target for Raspberry Pi commands
SSH_TARGET ?= rpi5

# Default target shows help
.DEFAULT_GOAL := help

## Audio Device Management (runs on rpi5)
audio-list: ## List all audio devices on the Raspberry Pi
	@ssh $(SSH_TARGET) "echo '=== USB Audio Devices ===' && lsusb | grep -i audio || echo 'No USB audio devices found'; \
	echo && echo '=== ALSA Playback Devices ===' && aplay -l; \
	echo && echo '=== ALSA Capture Devices ===' && arecord -l"

audio-status: ## Show detailed audio device configuration
	@ssh $(SSH_TARGET) "echo '=== Sound Cards ===' && cat /proc/asound/cards; \
	echo && echo '=== Loaded Audio Modules ===' && lsmod | grep -E 'snd_usb|snd_' | head -10; \
	echo && echo '=== USB Audio Details ===' && lsusb -v 2>/dev/null | grep -A 5 -B 5 -i audio | head -20"

## Help
help: ## Show this help message
	@echo 'Missing Link Project - Command Reference'
	@echo '======================================='
	@echo ''
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Variables:'
	@echo '  SSH_TARGET     Target host for SSH commands (default: rpi5)'
	@echo ''
	@echo 'Examples:'
	@echo '  make audio-list'
	@echo '  make audio-status'
	@echo '  SSH_TARGET=pi@192.168.4.1 make audio-list'

.PHONY: audio-list audio-status help