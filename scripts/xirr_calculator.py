#!/usr/bin/env python3
"""
XIRR Calculator for Paper Trading Account
Calculates Internal Rate of Return (XIRR) from daily performance data
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent.resolve()
PAPER_REPORTS_DIR = PROJECT_DIR / "reports" / "paper"
LEDGER_FILE = PAPER_REPORTS_DIR / "performance_ledger_paper.json"
METRICS_FILE = PAPER_REPORTS_DIR / "dashboard_metrics.json"

INCEPTION_DATE = datetime(2026, 5, 26)
INITIAL_INVESTMENT = 39254.53  # Actual equity at account inception (May 26 2026)

def load_ledger():
    if not LEDGER_FILE.exists():
        return {}
    with LEDGER_FILE.open() as f:
        return json.load(f)

def calculate_xirr(ledger):
    if not ledger:
        return {
            "xirr_percent": 0.0,
            "total_return_percent": 0.0,
            "market_value": INITIAL_INVESTMENT,
            "invested_value": INITIAL_INVESTMENT,
            "total_return_dollars": 0.0,
            "days_invested": 0,
            "status": "No data yet"
        }

    sorted_dates = sorted(ledger.keys())
    latest_snapshot = ledger[sorted_dates[-1]]
    latest_market_value = latest_snapshot.get("total_market_value", INITIAL_INVESTMENT)
    
    # Calculate returns
    total_return_dollars = latest_market_value - INITIAL_INVESTMENT
    total_return_percent = (total_return_dollars / INITIAL_INVESTMENT * 100) if INITIAL_INVESTMENT > 0 else 0
    
    # Calculate days invested
    first_date = datetime.fromisoformat(sorted_dates[0].replace("Z", "+00:00")) if "T" in sorted_dates[0] else datetime.fromisoformat(sorted_dates[0])
    last_date = datetime.fromisoformat(sorted_dates[-1].replace("Z", "+00:00")) if "T" in sorted_dates[-1] else datetime.fromisoformat(sorted_dates[-1])
    days_invested = (last_date - first_date).days + 1
    
    # Annualize the return (simple method)
    xirr_percent = 0.0
    if days_invested > 1:
        xirr_percent = ((latest_market_value / INITIAL_INVESTMENT) ** (365.25 / days_invested) - 1) * 100
    
    return {
        "xirr_percent": round(xirr_percent, 2),
        "total_return_percent": round(total_return_percent, 2),
        "market_value": round(latest_market_value, 2),
        "invested_value": INITIAL_INVESTMENT,
        "total_return_dollars": round(total_return_dollars, 2),
        "days_invested": days_invested,
        "latest_date": sorted_dates[-1],
        "status": "Calculated",
        "updated_at": datetime.now().isoformat()
    }

def main():
    ledger = load_ledger()
    metrics = calculate_xirr(ledger)
    
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_FILE.open("w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✅ Metrics calculated: {METRICS_FILE}")
    print(f"   Market Value: ${metrics['market_value']:,.2f}")
    print(f"   Total Return: {metrics['total_return_percent']:.2f}%")
    print(f"   XIRR: {metrics['xirr_percent']:.2f}%")

if __name__ == "__main__":
    main()
