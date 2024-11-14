# Namada Tools

A collection of tools for interacting with the Namada blockchain.

## Tools

### [Proposal Decoder](docs/proposal-decoder.md)

Tool for decoding and displaying Namada governance proposals in a human-readable format. Shows proposal details including content, voting epochs, status, and WASM data hashes.

```bash
python proposal_decoder.py --proposal-id <ID>
```

### [GitHub Artifacts Downloader](docs/artifacts-downloader.md) 

Downloads artifacts from Namada GitHub workflow runs and verifies WASM files by calculating their SHA256 hashes. Supports downloading from specific runs or automatically fetching the latest.

```bash
python github_downloader.py --run-id <ID>
```

## Development

1. Create a virtual environment (recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## License

[TBD]

## Contributing

[TBD]
