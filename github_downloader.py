import requests
import os
import zipfile
from urllib.parse import urlparse
from dotenv import load_dotenv
import sys
import hashlib
import glob
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class GitHubArtifactsDownloader:
    def __init__(self, token, owner, repo):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.api_base = "https://api.github.com"

    def get_latest_workflow_run_id(self):
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/runs"
        logger.debug(f"Fetching latest workflow run from {url}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        runs = response.json()["workflow_runs"]
        if not runs:
            raise ValueError("No workflow runs found")
        logger.debug(f"Found latest run ID: {runs[0]['id']}")
        return str(runs[0]["id"])

    def get_workflow_run(self, run_id):
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}"
        logger.debug(f"Fetching workflow run details from {url}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_artifacts_for_run(self, run_id):
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/artifacts"
        logger.debug(f"Fetching artifacts from {url}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()["artifacts"]

    def download_artifact(self, artifact_id, output_dir):
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/artifacts/{artifact_id}/zip"
        response = requests.get(url, headers=self.headers, stream=True)
        response.raise_for_status()

        os.makedirs(output_dir, exist_ok=True)
        zip_path = os.path.join(output_dir, f"artifact_{artifact_id}.zip")
        logger.info(f"Downloading to {zip_path}...")

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info("Extracting files...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(output_dir)
            logger.info(f"Files extracted to: {output_dir}")
            self.print_wasm_checksums(output_dir)

        except zipfile.BadZipFile:
            logger.error(
                "The downloaded file is not a valid zip file. Keeping the original downloaded file."
            )
            return

        os.remove(zip_path)

    def print_wasm_checksums(self, directory):
        wasm_files = glob.glob(os.path.join(directory, "**", "*.wasm"), recursive=True)

        if not wasm_files:
            logger.info("No .wasm files found in the artifacts.")
            return

        for wasm_file in sorted(wasm_files):
            sha256_hash = hashlib.sha256()
            with open(wasm_file, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            rel_path = os.path.relpath(wasm_file, directory)
            logger.info(f"Data Hash {rel_path}: {sha256_hash.hexdigest().upper()}")
            # Keep stdout output for user visibility
            print(f"Data Hash {rel_path}: {sha256_hash.hexdigest().upper()}")


def parse_github_url(url):
    path_parts = urlparse(url).path.strip("/").split("/")
    return path_parts[0], path_parts[1]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download and verify GitHub workflow artifacts"
    )
    parser.add_argument(
        "-r",
        "--run-id",
        type=str,
        help="Specific workflow run ID to download artifacts from (default: latest)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv()

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN not found in .env file")
        sys.exit(1)

    repo_url = "https://github.com/anoma/namada-governance-upgrades"
    owner, repo = parse_github_url(repo_url)

    downloader = GitHubArtifactsDownloader(github_token, owner, repo)

    try:
        run_id = args.run_id if args.run_id else downloader.get_latest_workflow_run_id()
        logger.info(f"Fetching artifacts for workflow run: {run_id}")

        run = downloader.get_workflow_run(run_id)
        print(f"Workflow: {run['name']}")
        print(f"Commit: {run['head_sha']}\n")

        artifacts = downloader.get_artifacts_for_run(run_id)
        if not artifacts:
            logger.info("No artifacts found for this workflow run")
            return

        for artifact in artifacts:
            logger.info(
                f"\nFound artifact: {artifact['name']} (Size: {artifact['size_in_bytes']} bytes)"
            )
            output_dir = f"artifacts/{run_id}/{artifact['name']}"
            downloader.download_artifact(artifact["id"], output_dir)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error occurred: {e}")


if __name__ == "__main__":
    main()
