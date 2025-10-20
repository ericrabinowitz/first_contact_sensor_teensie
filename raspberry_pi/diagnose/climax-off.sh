#!/bin/bash
# Deactivate climax mode by disconnecting all statues

set -e

# Sleep period between commands (in seconds)
SLEEP_PERIOD=0.5

echo "Deactivating climax mode - disconnecting all statues..."

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"eros", "emitters":[]}' && echo "✓ eros disconnected"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"elektra", "emitters":[]}' && echo "✓ elektra disconnected"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"ariel", "emitters":[]}' && echo "✓ ariel disconnected"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"sophia", "emitters":[]}' && echo "✓ sophia disconnected"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"ultimo", "emitters":[]}' && echo "✓ ultimo disconnected"

echo "✓ Climax mode deactivated"