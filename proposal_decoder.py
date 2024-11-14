import base64
import requests
import logging
import os
import argparse
from typing import Dict, List, Optional
from dotenv import load_dotenv
from borsh_construct import (
    CStruct,
    String,
    U8,
    U64,
    Option as BorshOption,
    TupleStruct,
    HashMap,
    Enum,
)

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get RPC URL from environment or use default
DEFAULT_RPC_URL = "http://localhost:26657"
RPC_URL = os.getenv("RPC_URL", DEFAULT_RPC_URL)


# Constants from Rust
HASH_LEN = 20
SHA_HASH_LEN = 32
ESTABLISHED_ADDRESS_BYTES_LEN = 21

# # Constants from the bech32m implementation
# CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
# BECH32M_CONST = 0x2BC830A3

# Constants from Rust bech32 implementation
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32M_CONST = 0x2BC830A3
CHECKSUM_LENGTH = 6
GENERATOR = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
HASH_LEN = 20
ADDR_ENCODING_LEN = 1 + HASH_LEN

# Define Address types
internal_address = Enum(
    "Implicit",
    "Established",
    "Pos",
    "SlashPool",
    "Parameters",
    "Governance",
    "Ibc",
    "EthBridge",
    "BridgePool",
    "Multitoken",
    "Pgf",
    "Erc20" / TupleStruct(U8[20]),  # ETH address is 20 bytes
    "Nut" / TupleStruct(U8[20]),
    "IbcToken" / TupleStruct(U8[20]),
    "Masp",
    "TempStorage",
    "ReplayProtection",
    enum_name="InternalAddress",
)

address = Enum(
    "Internal" / TupleStruct(internal_address),
    "Established" / TupleStruct(U8[20]),  # 20 byte hash
    "Implicit" / TupleStruct(U8[20]),  # 20 byte hash
    enum_name="Address",
)

# Define ProposalType enum
proposal_type = Enum(
    "Default",
    "DefaultWithWasm" / TupleStruct(U8[SHA_HASH_LEN]),  # 32 byte hash
    # Note: Simplified PGFSteward and PGFPayment for now as they're complex types
    "PGFSteward",
    "PGFPayment",
    enum_name="ProposalType",
)

# Define StorageProposal struct
storage_proposal = CStruct(
    "id" / U64,
    "content" / HashMap(String, String),
    "author" / address,
    "type" / proposal_type,
    "voting_start_epoch" / U64,
    "voting_end_epoch" / U64,
    "activation_epoch" / U64,
)

# Wrap StorageProposal in Option since that's how it's returned from RPC
optional_storage_proposal = BorshOption(storage_proposal)


class ProposalStatus:
    """Proposal status matching Rust implementation."""

    PENDING = "pending"
    ONGOING = "on-going"
    ENDED = "ended"

    def __init__(self, status: str):
        """Initialize with one of the defined statuses."""
        if status not in {self.PENDING, self.ONGOING, self.ENDED}:
            raise ValueError(f"Invalid status: {status}")
        self._status = status

    def __str__(self) -> str:
        """Match Rust's Display implementation."""
        return self._status


def print_bytes(label: str, data: bytes):
    """Helper to print bytes in a readable format."""
    print(f"{label}: {' '.join(f'{b:02x}' for b in data)}")


def bech32_encode_bytes(payload_bytes: bytes, hrp: str = "tnam") -> str:
    """Encode bytes using bech32m format.

    Follows Rust implementation:
    ```rust
    impl string_encoding::Format for Address {
        fn encode(&self) -> String {
            let base32 = self.to_bytes().to_base32();
            bech32::encode(Self::HRP, base32, BECH32M_VARIANT)
        }
    }
    ```
    """
    base32_words = bytes_to_base32_words(payload_bytes)
    return create_bech32m_string(hrp, base32_words)


def bech32_polymod(values: List[int]) -> int:
    """Internal function that computes the Bech32 checksum."""
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def bytes_to_base32_words(data: bytes) -> List[int]:
    """Convert bytes to 5-bit base32 words.

    Follows Rust bech32::ToBase32 trait implementation:
    ```rust
    impl ToBase32 for [u8] {
        fn to_base32(&self) -> Vec<u5> {
            let mut ret = Vec::new();
            let mut acc = 0u64;
            let mut bits = 0;
            for &value in self.iter() {
                acc = (acc << 8) | u64::from(value);
                bits += 8;
                while bits >= 5 {
                    bits -= 5;
                    ret.push(((acc >> bits) & 31) as u5);
                }
            }
            if bits > 0 {
                ret.push(((acc << (5 - bits)) & 31) as u5);
            }
            ret
        }
    }
    ```
    """
    logger.debug(f"Converting bytes to base32: {data.hex()}")
    words = []
    value = 0
    bits = 0

    for byte in data:
        value = (value << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            words.append((value >> bits) & 31)

    if bits > 0:
        words.append((value << (5 - bits)) & 31)

    logger.debug(f"Base32 words: {words}")
    return words


def create_bech32m_string(hrp: str, data: List[int]) -> str:
    """Create final bech32m string with checksum.

    Follows Rust bech32::encode implementation:
    ```rust
    pub fn encode(hrp: &str, data: &[u5], variant: Variant) -> String {
        let mut combined = hrp_expand(hrp);
        combined.extend(data);
        let checksum = create_checksum(hrp, data, variant);
        combined.extend(&checksum);
        let mut ret = String::with_capacity(hrp.len() + 1 + combined.len());
        ret.push_str(hrp);
        ret.push('1');
        for p in combined {
            ret.push(CHARSET[p.to_u8() as usize]);
        }
        ret
    }
    ```
    """
    expanded_hrp = expand_hrp(hrp)
    combined = expanded_hrp + data
    checksum = create_checksum(combined)

    return f"{hrp}1" + "".join(CHARSET[d] for d in data + checksum)


def expand_hrp(hrp: str) -> List[int]:
    """Expand HRP into values for checksum computation.

    From Rust bech32 implementation:
    ```rust
    fn hrp_expand(hrp: &str) -> Vec<u5> {
        let mut ret = Vec::with_capacity(hrp.len() * 2 + 1);
        ret.extend(hrp.bytes().map(|x| (x >> 5) as u5));
        ret.push(0);
        ret.extend(hrp.bytes().map(|x| (x & 31) as u5));
        ret
    }
    ```
    """
    logger.debug(f"Expanding HRP: {hrp}")
    result = [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
    logger.debug(f"Expanded HRP: {result}")
    return result


def create_checksum(values: List[int]) -> List[int]:
    """Create bech32m checksum from values.

    From Rust bech32::encode_checksummed_base32():
    ```rust
    let polymod = polymod(values) ^ variant.constant();
    (0..6).map(|i| ((polymod >> 5 * (5 - i)) & 31) as u5).collect()
    ```
    """
    polymod = bech32_polymod(values + [0] * 6) ^ BECH32M_CONST
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def format_address(addr) -> str:
    """Format address into human readable form using bech32m.

    Follows Rust Address implementation:
    ```rust
    impl string_encoding::Format for Address {
        type EncodedBytes<'a> = [u8; raw::ADDR_ENCODING_LEN];
        const HRP: &'static str = string_encoding::ADDRESS_HRP;

        fn to_bytes(&self) -> [u8; raw::ADDR_ENCODING_LEN] {
            let raw_addr: raw::Address<'_, _> = self.into();
            raw_addr.to_bytes()
        }
    }
    ```
    """
    if isinstance(addr, address.enum.Internal):
        return f"Internal({addr.tuple_data[0].__class__.__name__})"

    elif isinstance(addr, address.enum.Established):
        raw_bytes = bytes(addr.tuple_data[0])
        addr_bytes = bytearray(ADDR_ENCODING_LEN)
        addr_bytes[0] = 0  # Leading zero encodes to 'q' in base32
        addr_bytes[1:] = raw_bytes
        return bech32_encode_bytes(addr_bytes)

    elif isinstance(addr, address.enum.Implicit):
        raw_bytes = bytes(addr.tuple_data[0])
        addr_bytes = bytearray(ADDR_ENCODING_LEN)
        addr_bytes[0] = 0
        addr_bytes[1:] = raw_bytes
        return bech32_encode_bytes(addr_bytes)

    return "Unknown Address Type"


def fetch_proposal_data(proposal_id: int, node_url: str = RPC_URL) -> str:
    """Fetch proposal data from the RPC endpoint."""
    url = f"{node_url}/abci_query"
    params = {
        "path": f'"/vp/governance/proposal/{proposal_id}"',
        "data": "",
        "prove": "false",
    }

    logger.debug(f"Fetching proposal data...")
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise ValueError(f"Error fetching data: HTTP {response.status_code}")

    result = response.json()
    return result["result"]["response"]["value"]


def parse_proposal_data(value_base64: str) -> Dict:
    """Parse the base64 encoded proposal data using borsh-construct."""
    decoded_value = base64.b64decode(value_base64)
    logger.debug(
        f"Decoded proposal data ({len(decoded_value)} bytes): {decoded_value.hex()}"
    )

    # Parse the Option<StorageProposal>
    result = optional_storage_proposal.parse(decoded_value)
    if result is None:
        raise ValueError("Proposal not found (Option::None)")

    # Convert the parsed data into a more friendly format
    proposal_data = {
        "Proposal Id": result.id,
        "Content": dict(result.content),  # Convert from Container to dict
        "Author": format_address(result.author),
        "Type": format_proposal_type(result.type),
        "Voting Start Epoch": result.voting_start_epoch,
        "Voting End Epoch": result.voting_end_epoch,
        "Activation Epoch": result.activation_epoch,
    }

    # Add wasm hash if present
    if isinstance(result.type, proposal_type.enum.DefaultWithWasm):
        proposal_data["Data Hash"] = bytes(result.type.tuple_data[0]).hex().upper()

    return proposal_data


def format_proposal_type(ptype) -> str:
    """Format proposal type into human readable form."""
    if isinstance(ptype, proposal_type.enum.Default):
        return "Default"
    elif isinstance(ptype, proposal_type.enum.DefaultWithWasm):
        return "Default with Wasm"
    elif isinstance(ptype, proposal_type.enum.PGFSteward):
        return "PGF Steward"
    elif isinstance(ptype, proposal_type.enum.PGFPayment):
        return "PGF Payment"
    else:
        return "Unknown Type"


def get_proposal_status(proposal: Dict, current_epoch: int) -> ProposalStatus:
    """Determine the proposal status based on epochs.

    Matches Rust implementation of ProposalStatus:
    - PENDING: Not yet started (current_epoch < voting_start)
    - ONGOING: Voting in progress (voting_start <= current_epoch < voting_end)
    - ENDED: Voting ended (current_epoch >= voting_end)
    """
    voting_start = proposal["Voting Start Epoch"]
    voting_end = proposal["Voting End Epoch"]

    if current_epoch < voting_start:
        return ProposalStatus(ProposalStatus.PENDING)
    elif voting_start <= current_epoch < voting_end:
        return ProposalStatus(ProposalStatus.ONGOING)
    else:  # current_epoch >= voting_end
        return ProposalStatus(ProposalStatus.ENDED)


def fetch_current_epoch(node_url: str = RPC_URL) -> int:
    """Fetch the current epoch from the node."""
    url = f"{node_url}/abci_query"
    params = {"path": '"/shell/epoch"', "data": "", "prove": "false"}

    logger.debug("Fetching current epoch...")
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise ValueError(f"Error fetching epoch: HTTP {response.status_code}")

    result = response.json()
    value_base64 = result["result"]["response"]["value"]

    # Decode the base64 value and interpret as u64
    decoded_value = base64.b64decode(value_base64)
    epoch = U64.parse(decoded_value)

    return epoch


def display_proposal(proposal_data: Dict, current_epoch: int, status: str):
    """Display proposal data in the same order and format as the Namada CLI."""
    # First print the epoch
    print(f"\nLast committed epoch: {current_epoch}")

    # Print fields in CLI order
    print(f"Proposal Id: {proposal_data['Proposal Id']}")
    print(f"Type: {proposal_data['Type']}")
    print(f"Author: {proposal_data['Author']}")

    # Format content as a single-line JSON-like string
    content = proposal_data["Content"]
    content_str = "{" + ", ".join(f'"{k}": "{v}"' for k, v in content.items()) + "}"
    print(f"Content: {content_str}")

    # Print epochs using CLI naming
    print(f"Start Epoch: {proposal_data['Voting Start Epoch']}")
    print(f"End Epoch: {proposal_data['Voting End Epoch']}")
    print(f"Activation Epoch: {proposal_data['Activation Epoch']}")

    # Print status
    print(f"Status: {str(status)}")

    # Print hash if present (using CLI format with "Data Hash:")
    if "Data Hash" in proposal_data:
        print(f"Data Hash: {proposal_data['Data Hash']}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Decode Namada governance proposals")
    parser.add_argument(
        "-i",
        "--proposal-id",
        type=int,
        default=0,
        help="Proposal ID to query (default: 0)",
    )
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_args()

    if not os.path.exists(".env"):
        print("Warning: .env file not found. Using default RPC URL:", DEFAULT_RPC_URL)

    try:
        # First fetch the current epoch
        current_epoch = fetch_current_epoch()
        # Then fetch and parse the proposal
        value_base64 = fetch_proposal_data(args.proposal_id)
        proposal_data = parse_proposal_data(value_base64)
        status = get_proposal_status(proposal_data, current_epoch)

        display_proposal(proposal_data, current_epoch, status)

    except ValueError as e:
        print(f"Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Network error: Could not connect to {RPC_URL}")
        print(f"Error details: {e}")


if __name__ == "__main__":
    main()
