#!/usr/bin/env python3
"""
IBKR Paper Trading Account Flex Web Service pull script.
Reads IBKR_FLEX_TOKEN_PAPER and IBKR_FLEX_QUERY_ID_PAPER from ../.env.paper
Fetches the Flex statement and writes it to ../data/paper/ibkr_flex_paper_YYYY-MM-DD.xml
No third-party libraries required.
"""

import os
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
ENV_FILE = PROJECT_DIR / ".env.paper"
DATA_DIR = PROJECT_DIR / "data" / "paper"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService"
SEND_REQUEST_URL = BASE_URL + ".SendRequest"
GET_STATEMENT_URL = BASE_URL + ".GetStatement"
API_VERSION = "3"

MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 10


def load_env(env_path: Path) -> dict:
    """Parse a simple KEY=VALUE .env file."""
    env = {}
    if not env_path.exists():
        print(f"ERROR: {env_path} not found", file=sys.stderr)
        return env
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            env[key.strip()] = value
    return env


def fetch_url(url: str) -> str:
    """Perform a GET request and return the response body as a string."""
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} from IBKR: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error reaching IBKR: {e.reason}", file=sys.stderr)
        sys.exit(1)


def send_request(token: str, query_id: str) -> str:
    """Call SendRequest and return the ReferenceCode."""
    url = f"{SEND_REQUEST_URL}?token={token}&version={API_VERSION}&queryId={query_id}"
    response = fetch_url(url)
    root = ET.fromstring(response)
    ref_code = root.findtext("referenceCode")
    if not ref_code:
        print("ERROR: No referenceCode in SendRequest response", file=sys.stderr)
        sys.exit(1)
    return ref_code


def get_statement(token: str, reference_code: str) -> str:
    """Poll GetStatement until ready, then return the statement XML."""
    url = f"{GET_STATEMENT_URL}?token={token}&version={API_VERSION}&referenceCode={reference_code}"

    for attempt in range(MAX_RETRIES):
        response = fetch_url(url)
        root = ET.fromstring(response)
        status = root.findtext("queryStatus")

        if status == "Done":
            # Extract the FlexStatement
            flex_stmt = root.find("FlexStatements/FlexStatement")
            if flex_stmt is not None:
                return ET.tostring(flex_stmt, encoding="unicode")
            else:
                print("ERROR: No FlexStatement in response", file=sys.stderr)
                sys.exit(1)

        if attempt < MAX_RETRIES - 1:
            print(f"Status: {status}. Waiting {RETRY_DELAY_SECONDS}s before retry...", file=sys.stderr)
            time.sleep(RETRY_DELAY_SECONDS)

    print("ERROR: Max retries reached; statement not ready", file=sys.stderr)
    sys.exit(1)


def main():
    # Load from .env.paper file first; fall back to OS environment variables.
    # The fallback is essential for GitHub Actions where the file doesn't exist
    # but secrets are injected as environment variables.
    env = load_env(ENV_FILE) if ENV_FILE.exists() else {}
    token    = env.get("IBKR_FLEX_TOKEN_PAPER")    or os.environ.get("IBKR_FLEX_TOKEN_PAPER")
    query_id = env.get("IBKR_FLEX_QUERY_ID_PAPER") or os.environ.get("IBKR_FLEX_QUERY_ID_PAPER")

    if not token or not query_id:
        print("ERROR: IBKR_FLEX_TOKEN_PAPER or IBKR_FLEX_QUERY_ID_PAPER not found "
              "in .env.paper or environment variables", file=sys.stderr)
        sys.exit(1)

    print(f"[Paper Account] Requesting Flex statement (Query ID: {query_id})...")
    ref_code = send_request(token, query_id)
    print(f"[Paper Account] Reference code: {ref_code}")

    print("[Paper Account] Polling for statement...")
    stmt_xml = get_statement(token, ref_code)

    # Write to file
    today = date.today().isoformat()
    output_file = DATA_DIR / f"ibkr_flex_paper_{today}.xml"
    with output_file.open("w") as f:
        f.write(f"<?xml version='1.0' encoding='UTF-8'?>\n{stmt_xml}")

    print(f"[Paper Account] Success! Wrote to: {output_file}")


if __name__ == "__main__":
    main()
