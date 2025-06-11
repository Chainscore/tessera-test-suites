#!/bin/bash

# Deploy JAM Services to Network

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYGROUND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying JAM Services..."

# Ensure tools are available
if [ ! -x "$PLAYGROUND_DIR/bin/jamt" ]; then
    echo "❌ JAM tools not found. Run './scripts/setup.sh' first"
    exit 1
fi

# Check if builds directory exists
if [ ! -d "$PLAYGROUND_DIR/builds" ]; then
    echo "❌ No builds found. Run './scripts/build-services.sh' first"
    exit 1
fi

# Change to playground directory
cd "$PLAYGROUND_DIR"

# Configuration
RPC_URL="ws://localhost:19800"
GAS_LIMIT=10000000

# Track deployment results
SUCCESSFUL_DEPLOYMENTS=()
FAILED_DEPLOYMENTS=()

echo "🌐 Deploying to: $RPC_URL"
echo "⛽ Gas limit: $GAS_LIMIT"
echo ""

# Create deployment log directory
mkdir -p logs/deployments

# Function to deploy a service
deploy_service() {
    local service_name="$1"
    local bytecode_file="builds/${service_name}-service.jam"
    
    echo "📦 Deploying $service_name service..."
    
    if [ ! -f "$bytecode_file" ]; then
        echo "❌ Bytecode file not found: $bytecode_file"
        FAILED_DEPLOYMENTS+=("$service_name (no bytecode)")
        return 1
    fi
    
    local log_file="logs/deployments/${service_name}-$(date +%Y%m%d-%H%M%S).log"
    
    echo "🔄 Creating service on JAM network..."
    echo "📝 Deployment log: $log_file"
    
    # Deploy the service using jamt
    if ./bin/jamt create-service "$bytecode_file" $GAS_LIMIT 2>&1 | tee "$log_file"; then
        # Parse service ID from output
        local service_id=$(grep -o "Service [0-9a-f]\+" "$log_file" | grep -o "[0-9a-f]\+$" | head -1)
        
        if [ -n "$service_id" ]; then
            echo "✅ Service deployed successfully!"
            echo "   Service ID: $service_id"
            echo "   Log file: $log_file"
            
            # Save service info
            cat > "data/services/${service_name}.json" << EOF
{
    "name": "$service_name", 
    "service_id": "$service_id",
    "bytecode_file": "$bytecode_file",
    "deployed_at": "$(date -Iseconds)",
    "gas_limit": $GAS_LIMIT,
    "log_file": "$log_file"
}
EOF
            
            SUCCESSFUL_DEPLOYMENTS+=("$service_name ($service_id)")
        else
            echo "❌ Could not parse service ID from deployment output"
            FAILED_DEPLOYMENTS+=("$service_name (no service id)")
        fi
    else
        echo "❌ Deployment failed for $service_name"
        FAILED_DEPLOYMENTS+=("$service_name (deployment error)")
    fi
    
    echo ""
}

# Create directories
mkdir -p data/services

# Deploy services
for bytecode_file in builds/*.jam; do
    if [ -f "$bytecode_file" ]; then
        # Extract service name from filename
        service_name=$(basename "$bytecode_file" .jam | sed 's/-service$//')
        deploy_service "$service_name"
    fi
done

# Summary
echo "📊 Deployment Summary:"
echo "======================"

if [ ${#SUCCESSFUL_DEPLOYMENTS[@]} -gt 0 ]; then
    echo "✅ Successful deployments (${#SUCCESSFUL_DEPLOYMENTS[@]}):"
    for deployment in "${SUCCESSFUL_DEPLOYMENTS[@]}"; do
        echo "  - $deployment"
    done
    echo ""
fi

if [ ${#FAILED_DEPLOYMENTS[@]} -gt 0 ]; then
    echo "❌ Failed deployments (${#FAILED_DEPLOYMENTS[@]}):"
    for deployment in "${FAILED_DEPLOYMENTS[@]}"; do
        echo "  - $deployment"
    done
    echo ""
fi

# List deployed services
echo "📋 Deployed Services:"
if ls data/services/*.json 1> /dev/null 2>&1; then
    for service_file in data/services/*.json; do
        if [ -f "$service_file" ]; then
            name=$(jq -r '.name' "$service_file" 2>/dev/null || echo "unknown")
            service_id=$(jq -r '.service_id' "$service_file" 2>/dev/null || echo "unknown")
            deployed_at=$(jq -r '.deployed_at' "$service_file" 2>/dev/null || echo "unknown")
            echo "  - $name (ID: $service_id) deployed at $deployed_at"
        fi
    done
else
    echo "  (none)"
fi

echo ""
echo "🎯 Next steps:"
echo "  - Test services: ./scripts/test-services.sh"
echo "  - Monitor network: ./bin/jamtop"
echo "  - Check logs: tail -f logs/polkajam.log"

# Exit with error if any deployments failed
if [ ${#FAILED_DEPLOYMENTS[@]} -gt 0 ]; then
    exit 1
fi

echo "🎉 All services deployed successfully!" 