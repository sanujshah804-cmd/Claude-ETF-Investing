#!/usr/bin/env python3
"""
Dashboard Automation Orchestrator
Runs after daily Flex pull to:
1. Calculate XIRR and metrics
2. Embed data into dashboard HTML
3. Deploy to GitHub Pages

Run this AFTER: ibkr_flex_pull_paper.py and paper_account_aggregator.py
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent.resolve()
SCRIPTS_DIR = PROJECT_DIR / "scripts"
DASHBOARD_FILE = PROJECT_DIR / "dashboard.html"
GITHUB_DOCS_DIR = PROJECT_DIR / "docs"
PAPER_REPORTS_DIR = PROJECT_DIR / "reports" / "paper"

print(f"[Dashboard Automation] Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Step 1: Calculate XIRR and metrics
print("\n[Step 1] Calculating XIRR and metrics...")
try:
    result = subprocess.run(
        [sys.executable, SCRIPTS_DIR / "xirr_calculator.py"],
        capture_output=True,
        text=True,
        timeout=30
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR calculating XIRR: {e}")
    sys.exit(1)

# Step 2: Read JSON data files
print("\n[Step 2] Loading data files...")
try:
    metrics_file = PAPER_REPORTS_DIR / "dashboard_metrics.json"
    ledger_file = PAPER_REPORTS_DIR / "performance_ledger_paper.json"

    if not metrics_file.exists():
        print(f"ERROR: Metrics file not found at {metrics_file}")
        sys.exit(1)
    if not ledger_file.exists():
        print(f"ERROR: Ledger file not found at {ledger_file}")
        sys.exit(1)

    with open(metrics_file, 'r') as f:
        metrics_data = json.load(f)

    with open(ledger_file, 'r') as f:
        ledger_data = json.load(f)

    print(f"✅ Metrics loaded: {metrics_data.get('market_value', 'N/A')}")
    print(f"✅ Ledger loaded: {len(ledger_data)} date snapshots")
except Exception as e:
    print(f"ERROR loading JSON files: {e}")
    sys.exit(1)

# Step 3: Embed data into HTML and generate dashboard
print("\n[Step 3] Embedding data into dashboard HTML...")
try:
    # Read the dashboard template
    with open(DASHBOARD_FILE, 'r') as f:
        html_content = f.read()

    # Create JavaScript variables with the data
    metrics_json = json.dumps(metrics_data)
    ledger_json = json.dumps(ledger_data)

    # Find the script section and insert data
    insert_point = html_content.find("window.addEventListener('load', loadDashboard);")

    if insert_point == -1:
        print("ERROR: Could not find insertion point in HTML")
        sys.exit(1)

    # Insert the data before the load event listener
    data_script = f"""        // Embedded dashboard data (no fetch needed)
        const DASHBOARD_METRICS = {metrics_json};
        const DASHBOARD_LEDGER = {ledger_json};

"""

    html_with_data = html_content[:insert_point] + data_script + html_content[insert_point:]

    # Also update the fetch functions to use embedded data instead of fetching
    # Replace the fetch calls with direct data usage
    html_with_data = html_with_data.replace(
        "fetch('docs/paper/dashboard_metrics.json')",
        "Promise.resolve(DASHBOARD_METRICS)"
    )
    html_with_data = html_with_data.replace(
        "fetch('docs/paper/performance_ledger_paper.json')",
        "Promise.resolve(DASHBOARD_LEDGER)"
    )
    html_with_data = html_with_data.replace(
        "fetch('paper/dashboard_metrics.json')",
        "Promise.resolve(DASHBOARD_METRICS)"
    )
    html_with_data = html_with_data.replace(
        "fetch('paper/performance_ledger_paper.json')",
        "Promise.resolve(DASHBOARD_LEDGER)"
    )
    html_with_data = html_with_data.replace(
        "fetch('reports/paper/dashboard_metrics.json')",
        "Promise.resolve(DASHBOARD_METRICS)"
    )
    html_with_data = html_with_data.replace(
        "fetch('reports/paper/performance_ledger_paper.json')",
        "Promise.resolve(DASHBOARD_LEDGER)"
    )

    # Remove .then(response => response.json()) since we're not fetching
    html_with_data = html_with_data.replace(
        ".then(response => {\n                    if (!response.ok) throw new Error('Metrics not found');\n                    return response.json();\n                })",
        ""
    )
    html_with_data = html_with_data.replace(
        ".then(response => response.json())",
        ""
    )

    # Write to docs/index.html
    GITHUB_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = GITHUB_DOCS_DIR / "index.html"

    with open(output_file, 'w') as f:
        f.write(html_with_data)

    print(f"✅ Dashboard generated with embedded data at {output_file}")
    print(f"   File size: {len(html_with_data)} bytes")

    # Also write to root index.html — GitHub Pages serves from repo root
    root_index = PROJECT_DIR / "index.html"
    with open(root_index, 'w') as f:
        f.write(html_with_data)
    print(f"✅ Root index.html updated: {root_index}")

except Exception as e:
    print(f"ERROR generating dashboard: {e}")
    sys.exit(1)

print(f"\n✅ Dashboard automation complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Dashboard ready: https://sanujshah804-cmd.github.io/Claude-ETF-Investing/")
