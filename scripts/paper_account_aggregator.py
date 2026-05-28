#!/usr/bin/env python3
"""
Paper Account Position Aggregator
Parses daily Flex XML files, extracts positions, aggregates performance metrics.
Tracks: positions, market values, returns (day invested, YTD, MTD, etc.)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

PROJECT_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_DIR / "data" / "paper"
REPORTS_DIR = PROJECT_DIR / "reports" / "paper"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Performance ledger file
LEDGER_FILE = REPORTS_DIR / "performance_ledger_paper.json"

# Persistent cost basis file (price paid at first purchase, never overwritten)
COST_BASIS_FILE = REPORTS_DIR / "cost_basis_paper.json"

# Reference date: when paper account was created
PAPER_ACCOUNT_START_DATE = datetime(2026, 5, 26)  # Today


def parse_flex_xml(xml_file: Path) -> dict:
    """
    Parse IBKR Flex XML and extract positions.
    Returns: {
        'date': '2026-05-26',
        'positions': [
            {'symbol': 'IAU', 'quantity': 94, 'market_price': 84.87, 'market_value': 7972.14, 'percentage': 18.8},
            ...
        ],
        'total_market_value': 42452,
        'cash': 0
    }
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Extract statement date
    stmt_elem = root.find(".//FlexStatement")
    if stmt_elem is None:
        return None

    # IBKR Flex XML uses toDate in YYYYMMDD format (e.g. "20260526")
    raw_date = stmt_elem.get("toDate") or stmt_elem.get("periodEndString") or stmt_elem.get("fromDate", "unknown")
    # Convert YYYYMMDD → YYYY-MM-DD so datetime.fromisoformat() can parse it
    if raw_date != "unknown" and len(raw_date) == 8 and raw_date.isdigit():
        stmt_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    else:
        stmt_date = raw_date

    # Extract positions
    positions = []
    total_value = 0

    # Find OpenPositions section
    # IBKR Flex XML uses: position (qty), markPrice, positionValue — only SUMMARY rows
    for pos in root.findall(".//OpenPosition"):
        # Skip DETAIL-level rows to avoid double-counting
        if pos.get("levelOfDetail", "SUMMARY") == "DETAIL":
            continue
        symbol = pos.get("symbol")
        quantity = float(pos.get("position") or pos.get("quantity") or 0)
        market_price = float(pos.get("markPrice", 0))
        market_value = float(pos.get("positionValue") or pos.get("markValue") or 0)

        if symbol and quantity != 0:
            positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "market_price": market_price,
                "market_value": market_value,
            })
            total_value += market_value

    # Load persisted cost basis (price first paid per share)
    cost_basis_map = {}
    if COST_BASIS_FILE.exists():
        with COST_BASIS_FILE.open() as f:
            cost_basis_map = json.load(f)

    # Enrich positions with cost basis and P&L; update cost basis file for new symbols
    for pos in positions:
        sym = pos["symbol"]
        if sym not in cost_basis_map:
            # First time we see this symbol: record purchase price as cost basis
            cost_basis_map[sym] = pos["market_price"]

        cost_basis = cost_basis_map[sym]
        invested_amount = round(pos["quantity"] * cost_basis, 2)
        pnl_dollars = round(pos["market_value"] - invested_amount, 2)
        pnl_pct = round((pnl_dollars / invested_amount) * 100, 4) if invested_amount else 0.0

        pos["cost_basis"]      = cost_basis
        pos["invested_amount"] = invested_amount
        pos["pnl_dollars"]     = pnl_dollars
        pos["pnl_pct"]         = pnl_pct

    # Persist updated cost basis map
    with COST_BASIS_FILE.open("w") as f:
        json.dump(cost_basis_map, f, indent=2)

    # Read cash balance from the Flex XML
    cash_value = 0.0
    for cash_elem in root.findall(".//CashReport/CashBalance"):
        if cash_elem.get("currency") == "USD":
            cash_value = float(cash_elem.get("value", 0))

    # If the XML doesn't have a CashReport, fall back to reading the
    # EquitySummaryByReportDateInBase net-liquidation value to derive cash.
    if cash_value == 0.0:
        for eq in root.findall(".//EquitySummaryByReportDateInBase"):
            net_liq = eq.get("total")
            if net_liq:
                cash_value = max(0.0, round(float(net_liq) - total_value, 2))
                break

    # True account value = equity + cash
    total_account_value = round(total_value + cash_value, 2)

    # Calculate percentages based on full account value (equity + cash)
    for pos in positions:
        if total_account_value > 0:
            pos["percentage"] = round((pos["market_value"] / total_account_value) * 100, 2)

    return {
        "date": stmt_date,
        "timestamp": datetime.now().isoformat(),
        "positions": sorted(positions, key=lambda x: x["market_value"], reverse=True),
        "equity_value": round(total_value, 2),
        "cash_value": round(cash_value, 2),
        "total_market_value": total_account_value,   # equity + cash = true account value
    }


def calculate_returns(snapshot: dict, ledger: dict) -> dict:
    """
    Calculate returns metrics for the paper account.
    """
    total_value = snapshot["total_market_value"]
    snap_date = datetime.fromisoformat(snapshot["date"].replace("Z", "+00:00")).date() if "T" not in snapshot["date"] else datetime.fromisoformat(snapshot["date"]).date()

    # Day invested return
    days_invested = (snap_date - PAPER_ACCOUNT_START_DATE.date()).days + 1
    invested_value_start = 45493.66  # Total fill cost: May 26 ($39,055.77) + May 27 top-up ($6,437.89)

    total_return_dollars = total_value - invested_value_start
    total_return_pct = (total_return_dollars / invested_value_start * 100) if invested_value_start > 0 else 0

    # Annualized return (if more than 1 day)
    if days_invested > 1:
        days_in_year = 365
        annualized_return = ((total_value / invested_value_start) ** (days_in_year / days_invested) - 1) * 100
    else:
        annualized_return = 0

    # YTD (since Jan 1, 2026)
    ytd_start = datetime(2026, 1, 1).date()
    ytd_days = (snap_date - ytd_start).days + 1
    ytd_return_pct = total_return_pct if ytd_days > 0 else 0

    # MTD (since start of month)
    mtd_start = datetime(snap_date.year, snap_date.month, 1).date()
    mtd_days = (snap_date - mtd_start).days + 1
    mtd_return_pct = total_return_pct if mtd_days > 0 else 0  # Simplified; would need MTD snapshot data

    return {
        "snap_date": snap_date.isoformat(),
        "days_invested": days_invested,
        "total_invested": invested_value_start,
        "current_value": total_value,
        "total_return_dollars": round(total_return_dollars, 2),
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return_pct": round(annualized_return, 2),
        "ytd_return_pct": round(ytd_return_pct, 2),
        "mtd_return_pct": round(mtd_return_pct, 2),
    }


def update_ledger(snapshot: dict, returns: dict):
    """
    Update the performance ledger with the new snapshot.
    """
    ledger = {}
    if LEDGER_FILE.exists():
        with LEDGER_FILE.open() as f:
            ledger = json.load(f)

    snap_date = returns["snap_date"]
    ledger[snap_date] = {
        "timestamp": snapshot["timestamp"],
        "positions": snapshot["positions"],
        "equity_value": snapshot.get("equity_value", snapshot["total_market_value"]),
        "cash_value": snapshot.get("cash_value", 0.0),
        "total_market_value": snapshot["total_market_value"],   # equity + cash
        "total_invested_value": returns["total_invested"],
        "returns": returns,
    }

    with LEDGER_FILE.open("w") as f:
        json.dump(ledger, f, indent=2)

    return ledger


def main():
    # Find latest Flex XML file
    xml_files = sorted(DATA_DIR.glob("ibkr_flex_paper_*.xml"))
    if not xml_files:
        print("ERROR: No paper account Flex XML files found", file=sys.stderr)
        sys.exit(1)

    latest_xml = xml_files[-1]
    print(f"[Paper Aggregator] Parsing: {latest_xml.name}")

    snapshot = parse_flex_xml(latest_xml)
    if not snapshot:
        print("ERROR: Failed to parse Flex XML", file=sys.stderr)
        sys.exit(1)

    returns = calculate_returns(snapshot, {})
    ledger = update_ledger(snapshot, returns)

    print(f"[Paper Aggregator] Snapshot date: {returns['snap_date']}")
    print(f"[Paper Aggregator] Total value: ${returns['current_value']:,.2f}")
    print(f"[Paper Aggregator] Return: {returns['total_return_pct']:.2f}% (${returns['total_return_dollars']:,.2f})")
    print(f"[Paper Aggregator] Ledger updated: {LEDGER_FILE}")

    # Write summary
    summary = {
        "latest_snapshot": returns,
        "position_count": len(snapshot["positions"]),
        "last_updated": snapshot["timestamp"],
    }

    summary_file = REPORTS_DIR / "paper_account_summary.json"
    with summary_file.open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"[Paper Aggregator] Summary: {summary_file}")


if __name__ == "__main__":
    main()
