#!/usr/bin/env python3
"""
Dashboard Automation Orchestrator
Runs after daily Flex pull to:
1. Calculate XIRR and metrics
2. Copy dashboard to GitHub
3. Commit and push updates

Run this AFTER: ibkr_flex_pull_paper.py and paper_account_aggregator.py
"""

import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent.resolve()
SCRIPTS_DIR = PROJECT_DIR / "scripts"
DASHBOARD_FILE = PROJECT_DIR / "dashboard.html"
GITHUB_DOCS_DIR = PROJECT_DIR / "docs"

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

# Step 2: Copy dashboard to GitHub docs folder
print("\n[Step 2] Updating GitHub dashboard...")
try:
    GITHUB_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    github_dashboard = GITHUB_DOCS_DIR / "index.html"
    shutil.copy(DASHBOARD_FILE, github_dashboard)
    print(f"✅ Dashboard copied to {github_dashboard}")
except Exception as e:
    print(f"ERROR copying dashboard: {e}")
    sys.exit(1)

# Step 3: Commit and push to GitHub (optional - requires git setup)
print("\n[Step 3] Updating GitHub (optional)...")
print("Note: Full git automation requires additional setup")
print("For now, dashboard is updated locally at: docs/index.html")

print(f"\n✅ Dashboard automation complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Dashboard ready: https://sanujshah804-cmd.github.io/Claude-ETF-Investing/")
