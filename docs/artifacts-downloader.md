# GitHub Artifacts Downloader

Downloads and verifies artifacts from Namada GitHub workflow runs, with automatic WASM verification.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/andreidavid/namada-tools.git
    cd namada-tools
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file with your GitHub token:

    ```bash
    echo 'GITHUB_TOKEN="your-github-token"' > .env
    ```

## Usage

Download latest workflow artifacts:

```bash
python github_downloader.py
```

Download specific workflow artifacts:

```bash
python github_downloader.py --run-id <RUN_ID>
```

Example output:

```bash
Workflow: Earthly +build
Commit: 8e5d5b190d14f6bb0430dd2be8929268a4b8ee7c

Data Hash phase2.wasm: EAF15308CEC6A657EE42FC599259A3F8A7D629991EEF1E0917653C36176CA5FC
Data Hash phase3.wasm: 9E83094CF31A8581F5F48713B623831D0BE428059D825EEDAEF5C8060E998664
Data Hash phase4.wasm: 3C8FEB28AD360F3A0FD31CCB4E1151B49DF1C6939E81F8A390D60C83D5A3091A
Data Hash phase5.wasm: 4ABB3B66D41F8ADC549876D53F80C00A0DFD33E1BAA536503AA8858C51FF057E
```

Options:

- `-r, --run-id`: Specific workflow run ID (optional, defaults to latest)
- `-h, --help`: Show help message

## Requirements

- Python 3.7+
- Required Python packages:
  - python-dotenv
  - requests