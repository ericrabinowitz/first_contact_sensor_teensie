#!/bin/bash
# Simulate full climax mode by connecting all adjacent statue pairs in circular topology
# This triggers the special climax effect with all statues connected

set -e

# Sleep period between commands (in seconds)
SLEEP_PERIOD=0.5

echo "Triggering climax mode - connecting all adjacent statue pairs..."

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"eros", "emitters":["elektra", "ariel"]}' && echo "✓ eros ↔ elektra, ariel"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"elektra", "emitters":["eros", "ultimo"]}' && echo "✓ elektra ↔ eros, ultimo"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"ariel", "emitters":["eros", "sophia"]}' && echo "✓ ariel ↔ eros, sophia"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"sophia", "emitters":["ariel", "ultimo"]}' && echo "✓ sophia ↔ ariel, ultimo"

sleep "$SLEEP_PERIOD"

curl -s -H 'Content-Type: application/json' -X POST http://192.168.4.1:8080/contact \
  -d '{"detector":"ultimo", "emitters":["sophia", "elektra"]}' && echo "✓ ultimo ↔ sophia, elektra"

echo "✓ Climax mode activated"