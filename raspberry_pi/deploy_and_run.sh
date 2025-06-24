#!/bin/bash

# Deploy and run scripts on Raspberry Pi
# Usage: ./deploy_and_run.sh [script_name.py]

# Configuration
PI_HOST="pi@rpi"
PI_WORKSPACE="/home/pi/first_contact"
SCRIPT_TO_RUN="$1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect if we're in the raspberry_pi directory or the parent
CURRENT_DIR=$(basename "$(pwd)")
if [ "$CURRENT_DIR" = "raspberry_pi" ]; then
    # We're inside raspberry_pi, use current directory
    LOCAL_WORKSPACE="$(pwd)"
    SYNC_SOURCE="./"
else
    # We're in parent directory, look for raspberry_pi subdirectory
    if [ -d "raspberry_pi" ]; then
        LOCAL_WORKSPACE="$(pwd)/raspberry_pi"
        SYNC_SOURCE="./raspberry_pi/"
    else
        echo -e "${RED}Error: Cannot find raspberry_pi directory${NC}"
        echo "Run this script from either:"
        echo "  - The parent directory containing raspberry_pi/"
        echo "  - Inside the raspberry_pi/ directory"
        exit 1
    fi
fi

echo -e "${GREEN}=== Raspberry Pi Deploy & Run ===${NC}"
echo "Local workspace: $LOCAL_WORKSPACE"
echo "Remote workspace: $PI_WORKSPACE"
echo ""

# Check if we can connect to the Pi
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 $PI_HOST "echo 'SSH connection successful'"; then
    echo -e "${RED}Failed to connect to $PI_HOST${NC}"
    echo "Make sure:"
    echo "  1. The Pi is powered on and connected to the network"
    echo "  2. SSH is enabled on the Pi"
    echo "  3. Your SSH key is set up (~/.ssh/id_rsa or ~/.ssh/id_ed25519)"
    exit 1
fi

# Create remote workspace if it doesn't exist
echo -e "${YELLOW}Setting up remote workspace...${NC}"
ssh $PI_HOST "mkdir -p $PI_WORKSPACE/raspberry_pi/{audio_test,tone_detect_test,logs}"

# Sync files
echo -e "${YELLOW}Syncing files to Pi...${NC}"
echo "Syncing from: $SYNC_SOURCE"
rsync -avz --delete \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='logs/*.log' \
    --exclude='logs/*.txt' \
    $SYNC_SOURCE $PI_HOST:$PI_WORKSPACE/raspberry_pi/

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to sync files${NC}"
    exit 1
fi

echo -e "${GREEN}Files synced successfully!${NC}"

# If a script was specified, run it
if [ -n "$SCRIPT_TO_RUN" ]; then
    echo ""
    echo -e "${YELLOW}Running script: $SCRIPT_TO_RUN${NC}"
    echo "========================================" 
    
    # Determine the full path
    if [[ $SCRIPT_TO_RUN == raspberry_pi/* ]]; then
        REMOTE_SCRIPT="$PI_WORKSPACE/$SCRIPT_TO_RUN"
    else
        REMOTE_SCRIPT="$PI_WORKSPACE/raspberry_pi/$SCRIPT_TO_RUN"
    fi
    
    # Make it executable and run it
    ssh $PI_HOST "cd $PI_WORKSPACE && chmod +x $REMOTE_SCRIPT && $REMOTE_SCRIPT"
else
    echo ""
    echo "No script specified. Files synced only."
    echo "To run a script, use: $0 <script_path>"
    echo ""
    echo "Available scripts on Pi:"
    ssh $PI_HOST "cd $PI_WORKSPACE && find raspberry_pi -name '*.py' -type f | sort"
fi 