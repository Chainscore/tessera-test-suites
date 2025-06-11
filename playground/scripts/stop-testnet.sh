#!/bin/bash

# Stop PolkaJam Testnet

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYGROUND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🛑 Stopping JAM Testnet..."

# Check if PID file exists
PID_FILE="$PLAYGROUND_DIR/logs/testnet.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    
    if kill -0 $PID 2>/dev/null; then
        echo "🔄 Stopping PolkaJam testnet (PID: $PID)..."
        kill $PID
        
        # Wait for graceful shutdown
        for i in {1..15}; do
            if ! kill -0 $PID 2>/dev/null; then
                break
            fi
            echo "⏳ Waiting for graceful shutdown... ($i/15)"
            sleep 2
        done
        
        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            echo "💥 Force stopping testnet..."
            kill -9 $PID 2>/dev/null || true
            sleep 1
        fi
        
        echo "✅ PolkaJam testnet stopped"
    else
        echo "⚠️  PolkaJam testnet not running (stale PID file)"
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
else
    echo "⚠️  No PID file found"
    
    # Try to find and kill any polkajam-testnet processes
    if pgrep -f "polkajam-testnet" > /dev/null; then
        echo "🔍 Found running polkajam-testnet processes, stopping them..."
        pkill -f "polkajam-testnet" || true
        sleep 2
        echo "✅ Stopped stray processes"
    else
        echo "ℹ️  No polkajam-testnet processes found"
    fi
fi

# Clean up temporary files
echo "🧹 Cleaning up temporary files..."
rm -f "$PLAYGROUND_DIR/logs/testnet.pid"

echo "🏁 JAM Testnet stopped" 