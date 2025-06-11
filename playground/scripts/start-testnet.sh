#!/bin/bash

# Start PolkaJam Testnet (Multi-node)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYGROUND_DIR="$(dirname "$SCRIPT_DIR")"

# Ensure tools are available
if [ ! -x "$PLAYGROUND_DIR/bin/polkajam-testnet" ]; then
    echo "❌ JAM tools not found. Run './scripts/setup.sh' first"
    exit 1
fi

echo "🌐 Starting JAM Testnet (Multi-node)..."

# Create logs directory
mkdir -p "$PLAYGROUND_DIR/logs"

# Change to playground directory
cd "$PLAYGROUND_DIR"

# Configuration
BASE_RPC_PORT=20800
PARAMETERS="tiny"  # Use tiny parameters for faster testing

echo "⚙️  Configuration:"
echo "  📊 Validators: 6"
echo "  🚪 Base RPC port: $BASE_RPC_PORT"
echo "  📏 Parameters: $PARAMETERS"
echo ""

echo "🚀 Starting testnet at ws://localhost:$BASE_RPC_PORT"
echo "📝 Logs will be written to logs/testnet.log"
echo ""

# Start the testnet
./bin/polkajam-testnet \
    --base-rpc-port $BASE_RPC_PORT \
    --parameters $PARAMETERS \
    2>&1 | tee "logs/testnet.log" &

TESTNET_PID=$!
echo $TESTNET_PID > "logs/testnet.pid"

# Wait a moment for startup
sleep 3

if kill -0 $TESTNET_PID 2>/dev/null; then
    echo "✅ PolkaJam testnet started (PID: $TESTNET_PID)"
    echo ""
    echo "🎯 Network Information:"
    echo "  🌐 Primary RPC: ws://localhost:$BASE_RPC_PORT"
    
    echo ""
    echo "🔍 Monitor options:"
    echo "  - Logs: tail -f logs/testnet.log"
    echo "  - Network: ./bin/jamtop"
    echo "  - Status: ./scripts/monitor-testnet.sh"
    echo ""
    echo "🎯 Next steps:"
    echo "  - Deploy services: ./scripts/deploy-services.sh"
    echo "  - Test services: ./scripts/test-services.sh"
    echo ""
    echo "⏹️  To stop: ./scripts/stop-testnet.sh"
    
    echo "🟢 Testnet is running successfully!"
else
    echo "❌ Failed to start testnet. Check logs/testnet.log"
    exit 1
fi 