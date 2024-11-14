# Proposal Decoder

Decodes and displays Namada governance proposals in a human-readable format.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/namada-tools.git
    cd namada-tools
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file with your RPC endpoint:

    ```bash
    echo 'RPC_URL="http://x.y.z"' > .env
    ```

## Usage

Query a proposal by ID:

```bash
python proposal_decoder.py --proposal-id <ID>
```

Example output:

```bash
Last committed epoch: 15
Proposal Id: 0
Type: Default with Wasm
Author: tnam1qqgll8x8rz9fvtdv8q6n985za0vjvgyu0udxh7fp
Content: {"abstract": "Initialize phase 2...", "discussions-to": "https://forum.namada.net/...", "title": "Phase 1 -> 2"}
Start Epoch: 1
End Epoch: 13
Activation Epoch: 14
Status: ended
Data Hash: EAF15308CEC6A657EE42FC599259A3F8A7D629991EEF1E0917653C36176CA5FC
```

Options:

- `-i, --proposal-id`: Proposal ID to query (default: 0)
- `-h, --help`: Show help message

## Requirements

- Python 3.7+
- Required Python packages:
  - borsh-construct
  - python-dotenv
  - requests
