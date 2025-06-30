# Missing Link Project Makefile
# Commands for managing the Missing Link art installation

# Default SSH target for Raspberry Pi commands
SSH_TARGET ?= rpi5

# Project directories
PROJECT_ROOT := ~/workspace/first_contact_sensor_teensie
PI_CODE_ROOT := $(PROJECT_ROOT)/raspberry_pi
AUDIO_DIR := $(PI_CODE_ROOT)/audio
TONE_DIR := $(PI_CODE_ROOT)/tone_detect_test
CONTROLLER_DIR := $(PI_CODE_ROOT)/controller

# Python unbuffered output options
PYTHON_UNBUF := PYTHONUNBUFFERED=1 stdbuf -o0 -e0

# Default target shows help
.DEFAULT_GOAL := help

## File Synchronization
sync: ## Sync project files to Raspberry Pi
	@echo "Syncing project files to $(SSH_TARGET)..."
	@rsync -avz --exclude '.git' --exclude '*.pyc' --exclude '__pycache__' \
		--exclude 'teensy' --exclude '.vscode' --exclude '.DS_Store' \
		./ $(SSH_TARGET):~/workspace/first_contact_sensor_teensie/
	@echo "✓ Sync complete"

## Audio Device Management (runs on rpi5)
audio-list: ## List all audio devices on the Raspberry Pi
	@ssh $(SSH_TARGET) "echo '=== USB Audio Devices ===' && lsusb | grep -i audio || echo 'No USB audio devices found'; \
	echo && echo '=== ALSA Playback Devices ===' && aplay -l; \
	echo && echo '=== ALSA Capture Devices ===' && arecord -l"

audio-status: ## Show detailed audio device configuration
	@ssh $(SSH_TARGET) "echo '=== Sound Cards ===' && cat /proc/asound/cards; \
	echo && echo '=== Loaded Audio Modules ===' && lsmod | grep -E 'snd_usb|snd_' | head -10; \
	echo && echo '=== USB Audio Details ===' && lsusb -v 2>/dev/null | grep -A 5 -B 5 -i audio | head -20"

## Audio Testing
audio-deps: ## Install audio dependencies (PortAudio) on Raspberry Pi
	@ssh $(SSH_TARGET) "sudo apt update && sudo apt install -y libportaudio2 portaudio19-dev"

tone-test: sync ## Play test tone on USB audio devices (syncs files first)
	@ssh -t $(SSH_TARGET) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_UNBUF) ./tone_test.py'"

tone-detect-test: sync ## Run tone detection test with ELEKTRA->EROS wiring (syncs files first)
	@ssh -t $(SSH_TARGET) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_UNBUF) ./tone_detect_test.py'"

audio-test: sync ## Run multi-channel audio playback test (syncs files first)
	@ssh -t $(SSH_TARGET) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_UNBUF) ./audio_test.py'"

audio-demo: sync ## Run interactive multi-channel audio demo with channel toggles (syncs files first)
	@ssh -t $(SSH_TARGET) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_UNBUF) ./multichannel_audio_demo.py'"

freq-sweep: sync ## Run frequency sweep test to find optimal tone frequencies (syncs files first)
	@ssh -t $(SSH_TARGET) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_UNBUF) ./frequency_sweep_test.py'"

## Process Management
stop: ## Stop all running test scripts on Raspberry Pi
	@echo "Stopping running test scripts on $(SSH_TARGET)..."
	@ssh $(SSH_TARGET) "pkill -f 'tone_test.py|tone_detect_test.py|controller.py' || true"
	@echo "✓ Scripts stopped"

kill-all: ## Force kill all Python scripts on Raspberry Pi
	@echo "Force killing all Python scripts on $(SSH_TARGET)..."
	@ssh $(SSH_TARGET) "pkill -9 -f 'python|uv run' || true"
	@echo "✓ All Python processes killed"

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

.PHONY: sync audio-list audio-status audio-deps tone-test tone-detect-test freq-sweep audio-test stop kill-all help