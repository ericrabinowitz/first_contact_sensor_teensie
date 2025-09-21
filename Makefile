# Missing Link Project Makefile
# Commands for managing the Missing Link art installation

# Default SSH target for Raspberry Pi commands
# This has ip address 192.168.5.73.
SSH_TARGET ?= rpi5b

# Project directories
PROJECT_ROOT := ~/workspace/first_contact_sensor_teensie
PI_CODE_ROOT := $(PROJECT_ROOT)/raspberry_pi
AUDIO_DIR := $(PI_CODE_ROOT)/audio
TONE_DIR := $(PI_CODE_ROOT)/contact
CONTROLLER_DIR := $(PI_CODE_ROOT)/controller
WLED_DIR := $(PI_CODE_ROOT)/setup

# Python unbuffered output options
PYTHON_UNBUF := PYTHONUNBUFFERED=1 stdbuf -o0 -e0

# Python with proper module path
PYTHON_WITH_PATH := PYTHONPATH=$(PI_CODE_ROOT) $(PYTHON_UNBUF)

# SSH command alias for interactive sessions
SSH_EXEC := ssh -t $(SSH_TARGET)

# Default target shows help
.DEFAULT_GOAL := help

## File Synchronization
sync: ## Sync project files to Raspberry Pi
	@echo "Syncing project files to $(SSH_TARGET)..."
	@rsync -avz --exclude '.git' --exclude '*.pyc' --exclude '__pycache__' \
		--exclude 'teensy' --exclude '.vscode' --exclude '.DS_Store' \
		./ $(SSH_TARGET):~/workspace/first_contact_sensor_teensie/
	@echo "✓ Sync complete"

controller: sync ## Run multi-channel audio playback test (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(CONTROLLER_DIR) && DEBUG=1 $(PYTHON_WITH_PATH) ./controller.py'"

controller-test: sync ## Run controller with LED/WLED disabled for audio testing (syncs files first)
	@echo "Starting controller in TEST MODE (no LED control)..."
	@$(SSH_EXEC) "bash -l -c 'cd $(CONTROLLER_DIR) && TEST_MODE_NO_LEDS=1 $(PYTHON_WITH_PATH) ./controller.py'"

## Audio Device Management (runs on rpi5)
audio-list: ## List all audio devices on the Raspberry Pi
	@ssh $(SSH_TARGET) "echo '=== USB Audio Devices ===' && lsusb | grep -i audio || echo 'No USB audio devices found'; \
	echo && echo '=== ALSA Playback Devices ===' && aplay -l; \
	echo && echo '=== ALSA Capture Devices ===' && arecord -l"

audio-status: ## Show detailed audio device configuration
	@ssh $(SSH_TARGET) "echo '=== Sound Cards ===' && cat /proc/asound/cards; \
	echo && echo '=== Loaded Audio Modules ===' && lsmod | grep -E 'snd_usb|snd_' | head -10; \
	echo && echo '=== USB Audio Details ===' && lsusb -v 2>/dev/null | grep -A 5 -B 5 -i audio | head -20"

print-devices:
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./print_devices.py'"

## Audio Testing
audio-deps: ## Install audio dependencies (PortAudio) on Raspberry Pi
	@ssh $(SSH_TARGET) "sudo apt update && sudo apt install -y libportaudio2 portaudio19-dev"

tone-demo: sync ## Play test tone on USB audio devices (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./tone_demo.py'"

tone-detect-demo: sync ## Run tone detection demo with multi-statue detection (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./tone_detect_demo.py'"

tone-detect-test: sync ## Run tone detection demo with 5-second timeout for testing
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./tone_detect_demo.py --timeout 2'"

detect-test: sync ## Run detection-only demo with 5-second timeout for testing
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./detect_demo.py --timeout 5'"

detect-demo: sync ## Run standalone tone detection demo (detection only, no generation)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./detect_demo.py'"

audio-setup-test: sync ## Test audio setup with None behavior
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./test_audio_setup.py'"

signal-test: sync ## Run basic transmission unittest to verify tone generation and detection
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./test_basic_transmission.py'"

audio-test: sync ## Run multi-channel audio playback test (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./audio_test.py'"

audio-demo: sync ## Run interactive multi-channel audio demo with channel toggles (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./multichannel_audio_demo.py'"

## 8-Channel HiFiBerry DAC8x Testing
8ch-test: sync ## Run 8-channel HiFiBerry DAC8x test with interactive controls
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./eight_channel_test.py'"

8ch-generate-tones: sync ## Generate 8-channel test tone WAV file
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./eight_channel_test.py --generate tones --output test_8ch_tones.wav'"

8ch-generate-sweep: sync ## Generate 8-channel sweep test WAV file
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./eight_channel_test.py --generate sweep --output test_8ch_sweep.wav'"

8ch-generate-mixed: sync ## Generate 8-channel mixed waveform WAV file
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./eight_channel_test.py --generate mixed --output test_8ch_mixed.wav'"

8ch-list: ## List audio devices with 8+ channels
	@$(SSH_EXEC) "bash -l -c 'cd $(AUDIO_DIR) && $(PYTHON_WITH_PATH) ./eight_channel_test.py --list-devices'"

freq-sweep: sync ## Run frequency sweep test to find optimal tone frequencies (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./frequency_sweep_test.py'"

## TX Control Testing
tx-test: sync ## Run interactive ADG2188 TX switching test (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./adg2188_test.py'"

tx-test-sim: sync ## Run ADG2188 TX test in simulation mode (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./adg2188_test.py --simulate'"

tone-detect-tx: sync ## Run tone detection demo with TX control enabled (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./tone_detect_demo.py --tx-control'"

tone-detect-tx-sim: sync ## Run tone detection demo with TX control in simulation mode (syncs files first)
	@$(SSH_EXEC) "bash -l -c 'cd $(TONE_DIR) && $(PYTHON_WITH_PATH) ./tone_detect_demo.py --tx-simulate'"

wled-test: sync ## Run WLED test
	@$(SSH_EXEC) "bash -l -c 'cd $(WLED_DIR) && $(PYTHON_WITH_PATH) ./wled.py'"

## Process Management
stop: ## Stop all running test scripts on Raspberry Pi
	@echo "Stopping running test scripts on $(SSH_TARGET)..."
	@ssh $(SSH_TARGET) "pkill -f 'tone_demo.py|tone_detect_demo.py|controller.py' || true"
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

## Type Checking
typecheck: ## Run pytype type checker on Python code
	@echo "Running pytype type checker..."
	@cd raspberry_pi && pytype --config=../pytype.cfg .

typecheck-install: ## Install pytype
	@echo "Installing pytype..."
	@pip3 install pytype

## Linting
lint: ## Run ruff linter on Python code
	@echo "Running ruff linter..."
	@cd raspberry_pi && ruff check . --fix

lint-install: ## Install ruff linter
	@echo "Installing ruff..."
	@pip3 install ruff

.PHONY: sync audio-list audio-status audio-deps tone-test tone-detect-test freq-sweep audio-test audio-demo 8ch-test 8ch-generate-tones 8ch-generate-sweep 8ch-generate-mixed 8ch-list tx-test tx-test-sim tone-detect-tx tone-detect-tx-sim stop kill-all help typecheck typecheck-install lint lint-install print-devices controller controller-test