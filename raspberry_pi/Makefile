# Makefile for Raspberry Pi audio testing

.PHONY: help sync test-devices test-multi diagnose logs clean

help:
	@echo "Raspberry Pi Audio Testing Commands:"
	@echo "  make sync          - Sync all files to Pi"
	@echo "  make test-devices  - Test USB audio devices"
	@echo "  make test-multi    - Run multi-channel test"
	@echo "  make diagnose      - Run diagnostic script"
	@echo "  make logs          - Fetch logs from Pi"
	@echo "  make clean         - Clean logs and temp files"

sync:
	@./deploy_and_run.sh

test-devices:
	@./deploy_and_run.sh audio_test/test_usb_devices.py

test-multi:
	@./deploy_and_run.sh audio_test/multi_channel_test_simple.py

test-multi-fixed:
	@./deploy_and_run.sh audio_test/multi_channel_test_rpi_fixed.py

diagnose:
	@./deploy_and_run.sh audio_test/diagnose_usb_audio.py

logs:
	@echo "Fetching logs from Pi..."
	@mkdir -p logs
	@rsync -avz pi@rpi:/home/pi/first_contact/raspberry_pi/logs/ ./logs/
	@echo "Logs saved to ./logs/"

clean:
	@echo "Cleaning local logs..."
	@rm -f logs/*.log logs/*.txt
	@echo "Cleaning remote logs..."
	@ssh pi@rpi "rm -f /home/pi/first_contact/raspberry_pi/logs/*.log /home/pi/first_contact/raspberry_pi/logs/*.txt"

# Run any script by name
run-%:
	@./deploy_and_run.sh audio_test/$*.py 