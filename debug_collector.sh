#!/bin/bash

set -euo pipefail

# Configuration
NAMADA_BASE_DIR="${NAMADA_BASE_DIR:-$HOME/.local/share/namada}"
TEMP_DIR="/tmp/namada-debug-$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="$HOME/namada-debug-reports"
LOG_LINES=10000  # Number of lines to collect from journald
VALIDATOR_ALIAS="${1:-}" # Take first argument as validator alias, empty if not provided

# Ensure required commands exist
REQUIRED_COMMANDS="namada namadac namadaw cometbft journalctl zip curl jq sed strings"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse NAMADA_BASE_DIR from systemd service
get_base_dir_from_systemd() {
    systemctl cat namada 2>/dev/null | grep "NAMADA_BASE_DIR" | cut -d'=' -f2 || true
}

# Alternative way by checking the running process environment
get_base_dir_from_process() {
    local pid=$(pgrep namadan)
    if [[ -n "$pid" ]]; then
        # Get environment variables from the running process
        cat /proc/$pid/environ 2>/dev/null | tr '\0' '\n' | grep "NAMADA_BASE_DIR" | cut -d'=' -f2 || true
    fi
}

# Third option: check the default location
get_default_base_dir() {
    echo "$HOME/.local/share/namada"
}

# Function to determine base directory
determine_base_dir() {
    # First try environment variable
    local base_dir="${NAMADA_BASE_DIR:-}"
    
    # If not set, try systemd service
    if [[ -z "$base_dir" ]]; then
        base_dir=$(get_base_dir_from_systemd)
    fi

    # If still not found, try process environment
    if [[ -z "$base_dir" ]]; then
        base_dir=$(get_base_dir_from_process)
    fi

    # Fallback to default location
    if [[ -z "$base_dir" ]]; then
        base_dir=$(get_default_base_dir)
    fi

    echo "$base_dir"
}

determine_chain_id() {
    local base_dir="$1"
    local chain_id=""
    
    # First try to find chain.toml in subdirectories
    for dir in "$base_dir"/*; do
        if [[ -d "$dir" && ! "$dir" =~ pre-genesis$ && ! "$dir" =~ logs$ ]]; then
            local chain_toml="$dir/chain.toml"
            if [[ -f "$chain_toml" ]]; then
                # Extract chain_id from chain.toml, without any logging
                chain_id=$(grep '^chain_id = ' "$chain_toml" | cut -d'"' -f2)
                if [[ -n "$chain_id" ]]; then
                    break
                fi
            fi
        fi
    done

    if [[ -n "$chain_id" ]]; then
        echo "$chain_id"
        return 0
    else
        return 1
    fi
}

check_requirements() {
    log_info "Checking requirements..."
    
    missing_commands=()
    for cmd in $REQUIRED_COMMANDS; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -ne 0 ]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        log_info "Please install missing commands and try again"
        log_info "You can install them using:"
        log_info "sudo apt update && sudo apt install -y zip curl jq binutils"
        exit 1
    fi
}

sanitize_file() {
    local file="$1"
    log_info "Sanitizing $file"
    
    # Patterns to sanitize using sed with extended regex (-E flag)
    sed -i -E \
        -e 's/tnam1[a-zA-Z0-9]{38,45}/[REDACTED_ADDRESS]/g' \
        -e 's/tpknam1[a-zA-Z0-9]{38,45}/[REDACTED_PUBLIC_KEY]/g' \
        -e 's/zsnam1[a-zA-Z0-9]{38,45}/[REDACTED_SPENDING_KEY]/g' \
        -e 's/zvknam1[a-zA-Z0-9]{38,45}/[REDACTED_VIEWING_KEY]/g' \
        -e 's/znam1[a-zA-Z0-9]{38,45}/[REDACTED_PAYMENT_ADDRESS]/g' \
        -e 's/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[REDACTED_IP]/g' \
        -e 's/([^[:space:]]+@[^[:space:]]+\.[^[:space:]]+)/[REDACTED_EMAIL]/g' \
        -e 's/sk_[a-zA-Z0-9]{32,}/[REDACTED_SECRET_KEY]/g' \
        -e 's/"private_key"[[:space:]]*:[[:space:]]*"[^"]+"/\"private_key\": "[REDACTED]"/g' \
        -e 's/"mnemonic"[[:space:]]*:[[:space:]]*"[^"]+"/\"mnemonic\": "[REDACTED]"/g' \
        -e 's/[a-f0-9]{64}/[REDACTED_HEX_64]/g' \
        -e 's/password[[:space:]]*=[[:space:]]*[^[:space:]]+/password=[REDACTED]/g' \
        "$file"
}

collect_node_info() {
    local info_dir="$TEMP_DIR/node_info"
    mkdir -p "$info_dir"
    
    log_info "Collecting node information..."

    # Collect versions
    namada --version > "$info_dir/namada_version.txt" 2>&1 || echo "Failed to get Namada version" > "$info_dir/namada_version.txt"
    cometbft version > "$info_dir/cometbft_version.txt" 2>&1 || echo "Failed to get CometBFT version" > "$info_dir/cometbft_version.txt"

    # Collect chain and validator status
    if curl -s http://localhost:26657/status > "$info_dir/node_status.json" 2>/dev/null; then
        log_info "Successfully collected node status"
    else
        log_warn "Failed to get node status - node may not be running"
        echo "Node not running or RPC endpoint not accessible" > "$info_dir/node_status.json"
    fi

    # Try to get validator info if validator alias is provided
    if [ -n "$VALIDATOR_ALIAS" ]; then
        namadac validator-state --validator "$VALIDATOR_ALIAS" > "$info_dir/validator_state.txt" 2>&1 || \
        echo "Failed to get validator state for $VALIDATOR_ALIAS" > "$info_dir/validator_state.txt"
    else
        echo "No validator alias provided" > "$info_dir/validator_state.txt"
    fi

    # Get network peers
    curl -s http://localhost:26657/net_info > "$info_dir/net_info.json" 2>/dev/null || \
        echo "Failed to get network info" > "$info_dir/net_info.json"
}

collect_system_info() {
    local info_dir="$TEMP_DIR/system_info"
    mkdir -p "$info_dir"
    
    log_info "Collecting system information..."

    # OS and system info
    {
        echo "=== OS Release ==="
        cat /etc/os-release
        echo -e "\n=== Kernel Version ==="
        uname -a
        echo -e "\n=== CPU Info ==="
        lscpu
        echo -e "\n=== Memory Info ==="
        free -h
        echo -e "\n=== Disk Usage ==="
        df -h
    } > "$info_dir/system_info.txt"

    # Network info
    {
        echo "=== Network Interfaces ==="
        ip addr show
        echo -e "\n=== Network Stats ==="
        ss -tulpn
        echo -e "\n=== DNS Info ==="
        cat /etc/resolv.conf
    } > "$info_dir/network_info.txt" 2>&1

    # Process info
    ps aux | grep -E 'namada|cometbft' > "$info_dir/process_info.txt"
}

collect_configs() {
    local config_dir="$TEMP_DIR/configs"
    mkdir -p "$config_dir"
    
    log_info "Collecting configuration files..."
    
    # Main Namada configs
    local chain_dir="/nvme/namada/tududes-fragile.ba8b841cd08325"
    local files_to_copy=(
        "config.toml"
        "chain.toml"
        "parameters.toml"
        "tokens.toml"
        "validity-predicates.toml"
        "balances.toml"
    )

    for file in "${files_to_copy[@]}"; do
        if [[ -f "$chain_dir/$file" ]]; then
            log_info "Copying $file"
            cp "$chain_dir/$file" "$config_dir/"
        fi
    done

    # CometBFT configs
    local cometbft_config_dir="$chain_dir/cometbft/config"
    local cometbft_files=(
        "config.toml"
        "genesis.json"
        "addrbook.json"
    )

    for file in "${cometbft_files[@]}"; do
        if [[ -f "$cometbft_config_dir/$file" ]]; then
            log_info "Copying CometBFT $file"
            cp "$cometbft_config_dir/$file" "$config_dir/cometbft_$file"
        fi
    done

    # List what we collected
    log_info "Contents of config directory:"
    ls -la "$config_dir"
}

collect_logs() {
    local log_dir="$TEMP_DIR/logs"
    mkdir -p "$log_dir"
    
    log_info "Collecting logs..."

    # Collect detailed systemd journal logs
    log_info "Collecting systemd journal logs"
    journalctl -u namada -n 10000 > "$log_dir/namada_service.log" 2>/dev/null || \
        echo "No systemd logs found for namada service" > "$log_dir/namada_service.log"

    # Collect additional service info
    log_info "Collecting service status"
    systemctl status namada > "$log_dir/namada_service_status.log" 2>&1 || true

    # Collect CometBFT state
    local chain_dir="/nvme/namada/tududes-fragile.ba8b841cd08325"
    if [[ -f "$chain_dir/cometbft/data/priv_validator_state.json" ]]; then
        log_info "Collecting CometBFT validator state"
        cp "$chain_dir/cometbft/data/priv_validator_state.json" "$log_dir/cometbft_validator_state.json"
    fi

    # Instead of copying LevelDB log files, let's get some database stats
    log_info "Collecting database information"
    {
        echo "=== Database Directories Size ==="
        du -sh "$chain_dir/db" 2>/dev/null || echo "No db directory found"
        du -sh "$chain_dir/cometbft/data/"*.db 2>/dev/null || echo "No CometBFT db found"
        
        echo -e "\n=== Database Files ==="
        ls -la "$chain_dir/db/" 2>/dev/null || echo "No db directory found"
        ls -la "$chain_dir/cometbft/data/"*.db 2>/dev/null || echo "No CometBFT db found"
    } > "$log_dir/database_info.log"

    # List what we collected
    log_info "Contents of logs directory:"
    ls -la "$log_dir"
}

create_debug_archive() {
    mkdir -p "$OUTPUT_DIR"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local archive_name="namada-debug-$timestamp.zip"
    local archive_path="$OUTPUT_DIR/$archive_name"
    
    log_info "Creating debug archive..."
    
    # Create archive
    (cd "$TEMP_DIR" && zip -r "$archive_path" .)
    
    log_info "Debug information collected and saved to: $archive_path"
    log_info "Please check the contents before sharing!"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

main() {
    log_info "Starting Namada debug information collection..."
    
    # Determine base directory
    NAMADA_BASE_DIR=$(determine_base_dir)
    log_info "Using Namada base directory: $NAMADA_BASE_DIR"
    
    if [[ ! -d "$NAMADA_BASE_DIR" ]]; then
        log_error "Namada base directory not found at $NAMADA_BASE_DIR"
        exit 1
    fi

    # Determine chain ID (store in variable first, then log)
    CHAIN_ID=$(determine_chain_id "$NAMADA_BASE_DIR")
    if [[ -z "$CHAIN_ID" ]]; then
        log_error "Could not determine chain ID in $NAMADA_BASE_DIR"
        exit 1
    fi
    log_info "Found chain ID: $CHAIN_ID"

    # Set chain directory
    CHAIN_DIR="$NAMADA_BASE_DIR/$CHAIN_ID"
    log_info "Using chain directory: $CHAIN_DIR"
    
    # Create temp directory
    mkdir -p "$TEMP_DIR"
    
    # Ensure cleanup on script exit
    trap cleanup EXIT
    
    # Run all collection functions
    check_requirements
    collect_node_info
    collect_system_info
    collect_configs
    collect_logs
    create_debug_archive
    
    log_info "Debug collection completed successfully!"
}

# Run main function
main