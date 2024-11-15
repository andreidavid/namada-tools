# Debug Collector

A script to collect debug information from a running Namada node, sanitize sensitive data, and create a comprehensive debug report.

## Installation

1. Download the script:

    ```bash
    curl -O https://raw.githubusercontent.com/andreidavid/namada-tools/master/debug_collector.sh
    chmod +x debug_collector.sh
    ```

2. Install dependencies:

    ```bash
    sudo apt update && sudo apt install -y zip curl jq binutils
    ```

## Usage

Basic usage with automatic validator detection:

```bash
./debug_collector.sh
```

Specify validator alias:

```bash
./debug_collector.sh volaris
```

Example output:

```bash
[INFO] Starting Namada debug information collection...
[INFO] Using Namada base directory: /nvme/namada
[INFO] Found chain ID: logs
[INFO] Using chain directory: /nvme/namada/logs
[INFO] Checking requirements...
[INFO] Collecting node information...
[INFO] Successfully collected node status
[INFO] Collecting system information...
[INFO] Collecting configuration files...
[INFO] Copying config.toml
[INFO] Copying chain.toml
[INFO] Copying parameters.toml
[INFO] Copying tokens.toml
[INFO] Copying validity-predicates.toml
[INFO] Copying balances.toml
[INFO] Copying CometBFT config.toml
[INFO] Copying CometBFT genesis.json
[INFO] Copying CometBFT addrbook.json
[INFO] Contents of config directory:
total 4268
drwxrwxr-x 2 andrei andrei    4096 Nov 15 14:22 .
drwxrwxr-x 5 andrei andrei    4096 Nov 15 14:22 ..
-rw-r--r-- 1 andrei andrei 4325941 Nov 15 14:22 balances.toml
-rw-r--r-- 1 andrei andrei     312 Nov 15 14:22 chain.toml
-rw-r--r-- 1 andrei andrei     506 Nov 15 14:22 cometbft_addrbook.json
-rw-r--r-- 1 andrei andrei    2561 Nov 15 14:22 cometbft_config.toml
-rw-r--r-- 1 andrei andrei    3580 Nov 15 14:22 cometbft_genesis.json
-rw-rw-r-- 1 andrei andrei    3159 Nov 15 14:22 config.toml
-rw-r--r-- 1 andrei andrei    1279 Nov 15 14:22 parameters.toml
-rw-r--r-- 1 andrei andrei    1443 Nov 15 14:22 tokens.toml
-rw-r--r-- 1 andrei andrei      91 Nov 15 14:22 validity-predicates.toml
[INFO] Collecting logs...
[INFO] Collecting systemd journal logs
[INFO] Collecting service status
[INFO] Collecting CometBFT validator state
[INFO] Collecting database information
[INFO] Contents of logs directory:
total 2276
drwxrwxr-x 2 andrei andrei    4096 Nov 15 14:22 .
drwxrwxr-x 6 andrei andrei    4096 Nov 15 14:22 ..
-rw------- 1 andrei andrei     443 Nov 15 14:22 cometbft_validator_state.json
-rw-rw-r-- 1 andrei andrei   67121 Nov 15 14:22 database_info.log
-rw-rw-r-- 1 andrei andrei 2241106 Nov 15 14:22 namada_service.log
-rw-rw-r-- 1 andrei andrei    2742 Nov 15 14:22 namada_service_status.log
[INFO] Creating debug archive...
  adding: configs/ (stored 0%)
  adding: configs/validity-predicates.toml (deflated 41%)
  adding: configs/config.toml (deflated 58%)
  adding: configs/tokens.toml (deflated 73%)
  adding: configs/balances.toml (deflated 55%)
  adding: configs/cometbft_genesis.json (deflated 85%)
  adding: configs/chain.toml (deflated 32%)
  adding: configs/parameters.toml (deflated 55%)
  adding: configs/cometbft_config.toml (deflated 57%)
  adding: configs/cometbft_addrbook.json (deflated 48%)
  adding: logs/ (stored 0%)
  adding: logs/cometbft_validator_state.json (deflated 26%)
  adding: logs/database_info.log (deflated 87%)
  adding: logs/namada_service.log (deflated 89%)
  adding: logs/namada_service_status.log (deflated 61%)
  adding: node_info/ (stored 0%)
  adding: node_info/namada_version.txt (stored 0%)
  adding: node_info/net_info.json (deflated 66%)
  adding: node_info/node_status.json (deflated 38%)
  adding: node_info/cometbft_version.txt (stored 0%)
  adding: node_info/validator_state.txt (deflated 36%)
  adding: system_info/ (stored 0%)
  adding: system_info/system_info.txt (deflated 58%)
  adding: system_info/network_info.txt (deflated 72%)
  adding: system_info/process_info.txt (deflated 51%)
[INFO] Debug information collected and saved to: /home/andrei/namada-debug-reports/namada-debug-20241115_142215.zip
[INFO] Please check the contents before sharing!
[INFO] Debug collection completed successfully!
[INFO] Cleaning up temporary files...
```

## Collected Information

The debug report includes:

- Node information
  - Namada version
  - CometBFT version
  - Node status
  - Validator state (if applicable)
  - Network peers

- System information
  - OS details
  - CPU info
  - Memory usage
  - Disk usage
  - Network configuration

- Configuration files
  - Namada config.toml
  - CometBFT configs
  - Chain parameters
  - Other relevant configs

- Logs
  - Namada service logs
  - Service status
  - Database information

## Security

The script automatically sanitizes sensitive information including:

- Addresses
- Public keys
- Private keys
- IP addresses
- Email addresses
- Passwords

## Requirements

- Bash
- Running Namada node
- Required system tools:
  - zip
  - curl
  - jq
  - binutils (for `strings` command)

## Output Location

Debug reports are saved to:

```bash
$HOME/namada-debug-reports/namada-debug-YYYYMMDD_HHMMSS.zip
```

## Retrieving the Debug Report

To copy the debug report from a remote server:

```bash
scp user@server:/home/user/namada-debug-reports/namada-debug-*.zip .
```
