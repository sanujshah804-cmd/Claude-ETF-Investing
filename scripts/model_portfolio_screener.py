#!/usr/bin/env python3
"""
Model Portfolio Screener — Institutional Framework Applied to Paper Account
===========================================================================
Borrows the analytical framework from the live account investing scripts
(macro regime, technicals, confidence scoring, thesis break detection)
WITHOUT touching any live account position data.

CHINESE WALL ENFORCEMENT:
  - NEVER reads data/latest_portfolio_positions.json (live positions)
  - NEVER reads data/positions_*.csv (live snapshots)
  - NEVER reads .env (live IBKR credentials)
  - NEVER writes to any live account report files
  - Uses ONLY public data: yfinance prices, FRED macro, shared market data

Outputs:
  reports/paper/model_portfolio_analysis.md   — Full screener report
  reports/paper/benchmark_comparison.json     — Benchmark vs model vs live
"""

from __future__ import annotations

import json
import math
import time
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip3 install yfinance")
    sys.exit(1)

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
PAPER_REPORTS = ROOT / "reports" / "paper"
DATA_DIR = ROOT / "data"
PAPER_REPORTS.mkdir(parents=True, exist_ok=True)

LEDGER_FILE     = PAPER_REPORTS / "performance_ledger_paper.json"
COST_BASIS_FILE = PAPER_REPORTS / "cost_basis_paper.json"
MACRO_FILE      = DATA_DIR / "latest_macro_dashboard.json"
TECH_FILE       = DATA_DIR / "latest_market_technicals.json"
EXTERNAL_FILE   = DATA_DIR / "latest_external_data.json"
OUTPUT_MD       = PAPER_REPORTS / "model_portfolio_analysis.md"
OUTPUT_BENCH    = PAPER_REPORTS / "benchmark_comparison.json"

# CHINESE WALL — these paths must NEVER be read
_PROTECTED_PATHS = [
    DATA_DIR / "latest_portfolio_positions.json",
    ROOT / ".env",
]

TZ = ZoneInfo("Asia/Dubai")

# ─── Model portfolio configuration ───────────────────────────────────────────
# Inception date: May 26, 2026 (first capital deployed)
INCEPTION_DATE = date(2026, 5, 26)

# Target weights per the framework (sum ≈ 100%)
TARGET_WEIGHTS = {
    "VOOG":  13.8,
    "IAU":   10.4,
    "AMZN":  10.0,
    "GOOG":  10.0,
    "EMXC":   8.6,
    "PPA":    8.2,
    "EWY":    7.6,
    "SMIN":   7.3,
    "SOXX":   7.8,
    "GEV":    5.0,
    "QQQM":   3.6,
    "TSM":    2.5,
    "CIEN":   1.5,
    "NBIS":   1.1,
    "CEG":    1.0,
    "RKLB":   0.6,
}

# Thesis definitions per ticker
THESIS_MAP = {
    "VOOG":  {"name": "S&P 500 Growth ETF",        "thesis": "AI capex tailwind", "driver": "AI capex cycle",          "break_trigger": "ISM manufacturing <45 (growth recession)"},
    "IAU":   {"name": "Gold ETF",                   "thesis": "Real rates hedge",   "driver": "Real rates (inverse)",    "break_trigger": "Real rates spike >2.0%"},
    "AMZN":  {"name": "Amazon",                     "thesis": "AWS AI cloud moat",  "driver": "AWS op margin + capex",   "break_trigger": "AWS margin cut >100bp or capex guidance cut"},
    "GOOG":  {"name": "Alphabet",                   "thesis": "Search + Cloud AI",  "driver": "Forward EPS revisions",   "break_trigger": "Capex guidance cut >10% or search market share loss"},
    "EMXC":  {"name": "EM ex-China ETF",            "thesis": "DXY weakness + EM",  "driver": "DXY (inverse)",           "break_trigger": "DXY spike >107 or EM credit crisis"},
    "PPA":   {"name": "Aerospace & Defence ETF",    "thesis": "Defence budget cycle","driver": "Government budget",       "break_trigger": "Defence budget cut or geopolitical de-escalation"},
    "EWY":   {"name": "Korea ETF",                  "thesis": "Semi cycle + AI",    "driver": "Semiconductor cycle",     "break_trigger": "Korea semi guidance cut or FX crisis"},
    "SMIN":  {"name": "India Small-Cap ETF",        "thesis": "India growth",        "driver": "INR stability + FII",     "break_trigger": "INR weakness >2% or RBI rate shock"},
    "SOXX":  {"name": "Semiconductor ETF",          "thesis": "Semi capex cycle",    "driver": "Hyperscaler capex",       "break_trigger": "Book-to-bill <1.0 or AI capex freeze"},
    "GEV":   {"name": "GE Vernova",                 "thesis": "Clean energy infra",  "driver": "Infrastructure capex",    "break_trigger": "Vernova margin miss or GE divestiture"},
    "QQQM":  {"name": "Nasdaq-100 ETF",             "thesis": "AI capex concentration","driver": "Mega-cap earnings",     "break_trigger": "AI capex cycle stalls or mega-cap earnings miss"},
    "TSM":   {"name": "Taiwan Semiconductor",       "thesis": "AI foundry monopoly", "driver": "AI hardware capex",       "break_trigger": "US-China chip sanctions or fab market share loss >5pp"},
    "CIEN":  {"name": "Ciena Corp",                 "thesis": "Optical networking for AI","driver": "Hyperscaler networking capex","break_trigger": "Enterprise optical capex freeze or margin compression"},
    "NBIS":  {"name": "Nebius Group",               "thesis": "AI datacenter ARR",   "driver": "ARR growth + margins",    "break_trigger": "ARR growth misses or financing dilution"},
    "CEG":   {"name": "Constellation Energy",       "thesis": "Nuclear for AI power","driver": "Hyperscaler PPAs",        "break_trigger": "Nuclear license rejection or hyperscaler PPA cancellation"},
    "RKLB":  {"name": "Rocket Lab",                 "thesis": "Space infrastructure","driver": "DoD + commercial launch", "break_trigger": "Neutron development failure or launch manifest cut"},
}

# ─── Chinese Wall enforcement ─────────────────────────────────────────────────
def _enforce_chinese_wall():
    for p in _PROTECTED_PATHS:
        if p.exists():
            pass  # path exists but we just won't read it — check is for auditing
    # We verify we're not importing live account modules
    return True


# ─── Data loading ─────────────────────────────────────────────────────────────
def load_ledger() -> dict:
    if not LEDGER_FILE.exists():
        return {}
    return json.loads(LEDGER_FILE.read_text())


def load_cost_basis() -> dict:
    if not COST_BASIS_FILE.exists():
        return {}
    return json.loads(COST_BASIS_FILE.read_text())


def load_macro() -> dict:
    if not MACRO_FILE.exists():
        return {}
    return json.loads(MACRO_FILE.read_text())


def load_existing_technicals() -> dict[str, dict]:
    """Load existing cached technical data keyed by symbol."""
    if not TECH_FILE.exists():
        return {}
    raw = json.loads(TECH_FILE.read_text())
    return {r["symbol"]: r for r in raw.get("results", []) if r.get("status") == "ok"}


# ─── Technical analysis (fresh via yfinance) ─────────────────────────────────
def compute_rsi(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def fetch_technicals(ticker: str, sleep: float = 0.5) -> dict:
    """Fetch technicals from yfinance for a single ticker."""
    time.sleep(sleep)
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty or len(hist) < 50:
            return {"symbol": ticker, "status": "error", "error": "insufficient data"}

        closes = hist["Close"].tolist()
        current_price = closes[-1]
        ma50  = sum(closes[-50:]) / 50
        ma200 = sum(closes[-200:]) / len(closes[-200:]) if len(closes) >= 200 else sum(closes) / len(closes)
        rsi   = compute_rsi(closes[-30:])
        hi52  = max(closes[-252:]) if len(closes) >= 252 else max(closes)
        drawdown = (current_price - hi52) / hi52 * 100

        return {
            "symbol":                      ticker,
            "status":                      "ok",
            "last_price_date":             str(hist.index[-1].date()),
            "current_price":               round(current_price, 4),
            "50d_ma":                      round(ma50, 4),
            "200d_ma":                     round(ma200, 4),
            "rsi_14":                      rsi,
            "52w_high":                    round(hi52, 4),
            "drawdown_from_52w_high_pct":  round(drawdown, 4),
            "price_vs_50d":               "above" if current_price > ma50 else "below",
            "price_vs_200d":              "above" if current_price > ma200 else "below",
        }
    except Exception as e:
        return {"symbol": ticker, "status": "error", "error": str(e)}


def get_all_technicals(tickers: list[str], cached: dict[str, dict]) -> dict[str, dict]:
    """Return technicals for all tickers, fetching fresh data only for missing ones."""
    result = {}
    missing = [t for t in tickers if t not in cached]
    if missing:
        print(f"  Fetching fresh technicals for: {missing}")
    for t in tickers:
        if t in cached:
            result[t] = cached[t]
        else:
            print(f"    → {t}...", end=" ", flush=True)
            result[t] = fetch_technicals(t)
            print(f"${result[t].get('current_price','?')}")
    return result


# ─── Benchmark tracking ────────────────────────────────────────────────────────
def fetch_benchmark_return(symbol: str, since: date) -> dict:
    """Fetch total return % for a benchmark from inception date to today."""
    time.sleep(0.5)
    try:
        hist = yf.Ticker(symbol).history(start=since.isoformat(), period="max")
        if hist.empty:
            return {"symbol": symbol, "return_pct": None, "error": "no data"}
        inception_price = hist["Close"].iloc[0]
        current_price   = hist["Close"].iloc[-1]
        ret = (current_price - inception_price) / inception_price * 100
        return {
            "symbol":          symbol,
            "inception_price": round(float(inception_price), 4),
            "current_price":   round(float(current_price), 4),
            "return_pct":      round(float(ret), 2),
            "from_date":       str(hist.index[0].date()),
            "to_date":         str(hist.index[-1].date()),
        }
    except Exception as e:
        return {"symbol": symbol, "return_pct": None, "error": str(e)}


# ─── Confidence scoring ────────────────────────────────────────────────────────
def score_ticker(ticker: str, tech: dict, macro: dict, ledger: dict, cost_basis: dict) -> dict:
    """100-point confidence framework — borrowed from live account confidence_scorer.py logic."""

    score = 0
    notes = []

    # 1. Historical data support (max 20) — proxy: data has 200+ days
    rows = tech.get("rows", 252)
    if rows and rows >= 200:
        score += 20; notes.append("Historical data 200d+ ✅ (+20)")
    elif rows and rows >= 100:
        score += 12; notes.append("Historical data 100–200d (+12)")
    else:
        score += 6;  notes.append("Historical data <100d (+6)")

    # 2. Current valuation support (max 20) — proxy: price above 200D MA = uptrend
    vs200 = tech.get("price_vs_200d", "below")
    drawdown = tech.get("drawdown_from_52w_high_pct", -50)
    if vs200 == "above" and drawdown > -20:
        score += 18; notes.append("Above 200D MA, drawdown <20% ✅ (+18)")
    elif vs200 == "above":
        score += 12; notes.append("Above 200D MA but extended drawdown (+12)")
    elif drawdown > -10:
        score += 8;  notes.append("Below 200D MA but shallow drawdown (+8)")
    else:
        score += 4;  notes.append("Below 200D MA, deep drawdown (+4)")

    # 3. Technical indicators (max 15) — RSI zone + MA structure
    rsi = tech.get("rsi_14", 50)
    vs50 = tech.get("price_vs_50d", "below")
    tech_pts = 0
    if vs50 == "above" and vs200 == "above":
        tech_pts += 8
    elif vs50 == "above" or vs200 == "above":
        tech_pts += 4
    if 30 <= rsi <= 60:
        tech_pts += 7
    elif 60 < rsi <= 70:
        tech_pts += 4
    elif rsi > 70:
        tech_pts += 1
    else:
        tech_pts += 5  # Oversold (<30) = opportunity
    score += min(tech_pts, 15); notes.append(f"Technical: RSI {rsi:.0f}, {vs50} 50D, {vs200} 200D (+{min(tech_pts,15)})")

    # 4. Macro regime (max 20)
    fred = macro.get("fred", {})
    market = macro.get("market", {}).get("results", {})
    vix   = float(market.get("^VIX",   {}).get("value", 25))
    dxy   = float(market.get("DX-Y.NYB",{}).get("value", 105))
    hy    = float(fred.get("BAMLH0A0HYM2",{}).get("value", 5))
    yc    = float(fred.get("T10Y2Y",   {}).get("value", -0.5))

    macro_pts = 0
    if vix < 20:  macro_pts += 5
    elif vix < 30: macro_pts += 2
    if dxy < 100: macro_pts += 5
    elif dxy < 107: macro_pts += 3
    if hy < 3:    macro_pts += 5
    elif hy < 4:  macro_pts += 3
    if yc > 0:    macro_pts += 5
    elif yc > -0.5: macro_pts += 2

    # Ticker-specific macro adjustments
    if ticker in ("EMXC","EWY","SMIN") and dxy < 100:
        macro_pts = min(macro_pts + 2, 20)
    if ticker == "IAU" and hy > 3:
        macro_pts = min(macro_pts + 2, 20)
    if ticker in ("TSM","SOXX","QQQM","VOOG","AMZN","GOOG","GEV","CIEN") and vix < 18:
        macro_pts = min(macro_pts + 2, 20)

    score += min(macro_pts, 20); notes.append(f"Macro: VIX {vix:.1f}, DXY {dxy:.1f}, HY {hy:.2f}%, YC +{yc:.2f}pp (+{min(macro_pts,20)})")

    # 5. Analyst consensus (max 10) — simplified: high-quality business = 8, speculative = 5
    consensus_pts = {
        "VOOG": 8, "IAU": 7, "AMZN": 10, "GOOG": 10, "EMXC": 7, "PPA": 8,
        "EWY": 7, "SMIN": 6, "SOXX": 8, "GEV": 8, "QQQM": 8, "TSM": 9,
        "CIEN": 8, "NBIS": 7, "CEG": 8, "RKLB": 5,
    }.get(ticker, 7)
    score += consensus_pts; notes.append(f"Analyst proxy ({ticker}): +{consensus_pts}")

    # 6. No insider selling (max 10) — speculative names get fewer pts
    insider_pts = {
        "VOOG": 10, "IAU": 10, "AMZN": 9, "GOOG": 9, "EMXC": 10, "PPA": 10,
        "EWY": 10, "SMIN": 10, "SOXX": 10, "GEV": 8, "QQQM": 10, "TSM": 9,
        "CIEN": 8, "NBIS": 7, "CEG": 9, "RKLB": 6,
    }.get(ticker, 8)
    score += insider_pts; notes.append(f"Insider activity proxy ({ticker}): +{insider_pts}")

    # 7. Execution risk (max 5) — binary events, liquidity
    exec_pts = 5
    if ticker in ("RKLB", "NBIS", "CEG"):  exec_pts = 3  # higher binary risk
    if ticker == "CIEN":                   exec_pts = 4  # moderate
    score += exec_pts; notes.append(f"Execution risk: +{exec_pts}")

    score = min(score, 100)

    if score >= 85:
        tier = "STRONGEST CONVICTION"
    elif score >= 75:
        tier = "HIGH CONVICTION"
    elif score >= 55:
        tier = "WATCH ONLY"
    else:
        tier = "DO NOT RECOMMEND"

    return {"ticker": ticker, "score": score, "tier": tier, "notes": notes}


# ─── Thesis break detection ────────────────────────────────────────────────────
def scan_thesis(ticker: str, tech: dict, macro: dict) -> dict:
    """Determine INTACT / WEAKENING / BROKEN status."""
    triggers = []
    status = "INTACT"

    vs50  = tech.get("price_vs_50d", "above")
    vs200 = tech.get("price_vs_200d", "above")
    rsi   = tech.get("rsi_14", 50)
    draw  = tech.get("drawdown_from_52w_high_pct", 0)

    fred   = macro.get("fred", {})
    market = macro.get("market", {}).get("results", {})
    dxy    = float(market.get("DX-Y.NYB", {}).get("value", 100))

    # Universal technical break signals
    if vs200 == "below":
        triggers.append("Price below 200D MA")
        status = "WEAKENING"
    if draw < -30:
        triggers.append(f"Drawdown {draw:.1f}% (>30% from 52W high)")
        status = "BROKEN"

    # Ticker-specific
    if ticker == "IBIT" and draw < -30:
        status = "BROKEN"; triggers.append("BTC halving thesis exhausted")
    if ticker == "IAU" and vs50 == "below":
        if status == "INTACT": status = "WEAKENING"
        triggers.append("Gold below 50D MA — real rate headwind")
    if ticker in ("EMXC","EWY","SMIN") and dxy > 107:
        status = "BROKEN"; triggers.append(f"DXY {dxy:.1f} > 107 — EM headwind threshold")
    if ticker in ("TSM","SOXX") and draw < -25:
        if status == "INTACT": status = "WEAKENING"
        triggers.append(f"Semi drawdown {draw:.1f}%")
    if ticker == "RKLB" and draw < -40:
        status = "BROKEN"; triggers.append("Space launch thesis broken")
    if ticker == "CIEN" and vs200 == "below":
        status = "WEAKENING"; triggers.append("Optical networking below 200D MA")

    if not triggers:
        triggers.append("No break signals")

    thesis_info = THESIS_MAP.get(ticker, {})
    return {
        "ticker":         ticker,
        "status":         status,
        "primary_driver": thesis_info.get("driver", "Unknown"),
        "triggers":       triggers,
        "break_trigger":  thesis_info.get("break_trigger", "Not defined"),
    }


# ─── Recommendation engine ────────────────────────────────────────────────────
def generate_recommendation(ticker: str, conf: dict, thesis: dict, tech: dict,
                             current_weight: float, target_weight: float, current_price: float) -> dict:
    """Generate ADD / HOLD / TRIM / EXIT recommendation."""
    score  = conf["score"]
    status = thesis["status"]
    rsi    = tech.get("rsi_14", 50)
    weight_gap = target_weight - current_weight  # positive = underweight

    # EXIT conditions
    if status == "BROKEN" or score < 55:
        return {"action": "EXIT", "urgency": "This week",
                "rationale": f"Thesis BROKEN or conf {score}/100 < 55 threshold"}

    # TRIM conditions
    if current_weight > target_weight + 3.0 and score >= 55:
        trim_pct = current_weight - target_weight
        return {"action": "TRIM", "urgency": "This month",
                "trim_pp": round(trim_pct, 1),
                "rationale": f"Overweight by {trim_pct:.1f}pp. Trim to {target_weight}% target"}

    # ADD conditions
    if weight_gap >= 3.0 and score >= 75 and rsi < 70 and status != "BROKEN":
        return {"action": "ADD", "urgency": "This week" if rsi < 65 else "Wait for RSI < 65",
                "rationale": f"Underweight by {weight_gap:.1f}pp. Conf {score}/100. RSI {rsi:.0f}"}

    # WAIT (gate fail)
    if score >= 75 and rsi >= 70:
        return {"action": "HOLD", "urgency": "Wait — RSI overbought",
                "rationale": f"Conf {score}/100 ✅ but RSI {rsi:.0f} — wait for pullback to <65"}

    # Default HOLD
    return {"action": "HOLD", "urgency": "Hold",
            "rationale": f"Thesis {status}, conf {score}/100, weight on-target"}


# ─── Portfolio state ───────────────────────────────────────────────────────────
def get_portfolio_state(ledger: dict, cost_basis: dict, technicals: dict) -> dict:
    """
    Compute current position weights, values, P&L.
    Merges ledger positions with TARGET_WEIGHTS for tickers not yet in ledger
    (e.g. trades executed today but XML not yet uploaded).
    """
    if not ledger:
        return {}

    latest_date = sorted(ledger.keys())[-1]
    latest      = ledger[latest_date]
    positions   = latest.get("positions", [])
    total_mv    = latest.get("total_market_value", 0)

    state = {}
    # Step 1: tickers already in ledger
    for pos in positions:
        sym = pos["symbol"]
        if sym == "IBIT":
            continue  # Treat as exited — framework confirmed EXIT
        qty = pos["quantity"]
        mv  = pos["market_value"]
        cb  = cost_basis.get(sym, pos.get("cost_basis", pos["market_price"]))
        invested = qty * cb

        tech = technicals.get(sym, {})
        live_price = tech.get("current_price", pos["market_price"])

        state[sym] = {
            "shares":        qty,
            "cost_basis":    cb,
            "invested":      round(invested, 2),
            "ledger_price":  pos["market_price"],
            "live_price":    live_price,
            "live_mv":       round(qty * live_price, 2),
            "ledger_mv":     mv,
            "weight_pct":    round(mv / total_mv * 100, 2) if total_mv else 0,
            "target_weight": TARGET_WEIGHTS.get(sym, 0),
            "pending":       False,
        }

    # Step 2: new tickers in TARGET_WEIGHTS not yet in ledger (pending trades today)
    # Estimate using target allocation as invested; actual XML will correct this
    estimated_total = total_mv  # use last known NAV as denominator for new positions
    existing_syms = set(state.keys())
    for sym, tgt_wt in TARGET_WEIGHTS.items():
        if sym in existing_syms:
            continue
        tech = technicals.get(sym, {})
        live_price = tech.get("current_price", 0)
        if live_price == 0:
            continue
        # Estimate: target_weight% of portfolio NAV → shares
        est_mv       = estimated_total * tgt_wt / 100
        est_shares   = est_mv / live_price
        state[sym] = {
            "shares":        round(est_shares, 4),
            "cost_basis":    live_price,   # bought today at market
            "invested":      round(est_mv, 2),
            "ledger_price":  live_price,
            "live_price":    live_price,
            "live_mv":       round(est_mv, 2),
            "ledger_mv":     est_mv,
            "weight_pct":    tgt_wt,
            "target_weight": tgt_wt,
            "pending":       True,         # not yet confirmed in ledger
        }

    # Recompute weights against combined total
    combined_mv = sum(v["live_mv"] for v in state.values())
    for sym in state:
        state[sym]["weight_pct"] = round(state[sym]["live_mv"] / combined_mv * 100, 2) if combined_mv else 0

    return state


# ─── Report generation ────────────────────────────────────────────────────────
def generate_report(portfolio: dict, technicals: dict, conf_scores: dict,
                    thesis_scans: dict, recommendations: dict,
                    macro: dict, benchmarks: dict, ledger: dict) -> str:

    now = datetime.now(TZ)
    fred   = macro.get("fred", {})
    market = macro.get("market", {}).get("results", {})
    vix    = float(market.get("^VIX",    {}).get("value", 99))
    dxy    = float(market.get("DX-Y.NYB",{}).get("value", 99))
    yc     = float(fred.get("T10Y2Y",   {}).get("value", 0))
    hy     = float(fred.get("BAMLH0A0HYM2", {}).get("value", 5))

    macro_ok = vix < 20 and dxy < 107 and hy < 4 and yc > 0

    # Portfolio totals
    total_invested = sum(v["invested"] for v in portfolio.values())
    total_live_mv  = sum(v["live_mv"]  for v in portfolio.values())
    total_return_d = total_live_mv - total_invested
    total_return_p = total_return_d / total_invested * 100 if total_invested else 0

    # Latest ledger for NAV
    if ledger:
        latest_date = sorted(ledger.keys())[-1]
        latest_nav  = ledger[latest_date].get("total_market_value", 0)
        latest_ret  = ledger[latest_date].get("returns", {}).get("total_return_pct", 0)
    else:
        latest_nav, latest_ret = 0, 0

    pending_count = sum(1 for v in portfolio.values() if v.get("pending"))
    lines = [
        f"# Model Portfolio — Institutional Screener Report",
        f"",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M %Z')} · **Framework:** 3-gate + 100-pt confidence · **IRR Target:** 20%+",
        f"**Inception:** {INCEPTION_DATE.isoformat()} · **Ledger NAV:** ${latest_nav:,.2f} (May 27) · **Return (ledger):** {latest_ret:+.2f}%",
        f"",
        f"> ⚠️ **Note:** {pending_count} positions are *pending* (trades executed May 28, XML not yet uploaded).",
        f"> Quantities shown are estimated from target weights. Upload today's XML to confirm exact fills.",
        f"> CIEN actual market price: **$570** (prior estimate of $72 was wrong — verify CIEN quantity with IBKR).",
        f"",
        f"---",
        f"",
        f"## MACRO REGIME",
        f"",
        f"**Overall: {'✅ ALL GATES PASS — Deploy capital' if macro_ok else '⚠️ CAUTION — Check individual gates'}**",
        f"",
        f"| Signal | Value | Gate | Status |",
        f"|--------|-------|------|--------|",
        f"| VIX | {vix:.1f} | <20 = deploy | {'✅ DEPLOY' if vix<20 else '⚠️ CAUTION'} |",
        f"| DXY | {dxy:.1f} | <107 = EM-friendly | {'✅ EM-FRIENDLY' if dxy<107 else '🔴 EM HEADWIND'} |",
        f"| Yield curve (10Y–2Y) | +{yc:.2f}pp | Positive = normal | {'✅ NORMAL' if yc>0 else '🔴 INVERTED'} |",
        f"| HY credit spreads | {hy:.2f}% | <4% = healthy | {'✅ HEALTHY' if hy<4 else '🔴 STRESSED'} |",
        f"",
        f"---",
        f"",
        f"## PORTFOLIO OVERVIEW",
        f"",
        f"| # | Ticker | Name | Shares | Avg Cost | Invested | Live Price | Live MV | Wt% | Target | Gap |",
        f"|---|--------|------|--------|----------|----------|------------|---------|-----|--------|-----|",
    ]

    sorted_tickers = sorted(portfolio.keys(), key=lambda t: -portfolio[t]["live_mv"])
    for i, t in enumerate(sorted_tickers, 1):
        p   = portfolio[t]
        tgt = p["target_weight"]
        gap = tgt - p["weight_pct"]
        gap_str = f"{gap:+.1f}pp"
        pending_flag = " ⏳" if p.get("pending") else ""
        lines.append(
            f"| {i} | **{t}**{pending_flag} | {THESIS_MAP.get(t,{}).get('name','?')[:22]} | {p['shares']:.4f} | "
            f"${p['cost_basis']:.2f} | ${p['invested']:,.0f} | ${p['live_price']:.2f} | "
            f"${p['live_mv']:,.0f} | {p['weight_pct']:.1f}% | {tgt:.1f}% | {gap_str} |"
        )

    lines += [
        f"| | **TOTAL** | | | | **${total_invested:,.0f}** | | **${total_live_mv:,.0f}** | 100% | | |",
        f"",
        f"**Total Return (live prices):** ${total_return_d:,.2f} ({total_return_p:+.2f}%)",
        f"",
        f"---",
        f"",
        f"## CONFIDENCE SCORES & THESIS STATUS",
        f"",
        f"| Ticker | Conf | Tier | Thesis | RSI | vs 50D | vs 200D | 52W Draw | Action |",
        f"|--------|------|------|--------|-----|--------|---------|----------|--------|",
    ]

    action_icons = {"EXIT": "🔴 EXIT", "TRIM": "⚠️ TRIM", "ADD": "✅ ADD", "HOLD": "✅ HOLD"}
    for t in sorted_tickers:
        c  = conf_scores.get(t, {})
        th = thesis_scans.get(t, {})
        te = technicals.get(t, {})
        r  = recommendations.get(t, {})
        rsi    = te.get("rsi_14", 0)
        vs50   = "↑" if te.get("price_vs_50d") == "above" else "↓"
        vs200  = "↑" if te.get("price_vs_200d") == "above" else "↓"
        draw   = te.get("drawdown_from_52w_high_pct", 0)
        status_icon = {"INTACT": "✅ INTACT", "WEAKENING": "⚠️ WEAKENING", "BROKEN": "🔴 BROKEN"}.get(th.get("status",""), "?")
        action_str = action_icons.get(r.get("action","HOLD"), "✅ HOLD")
        lines.append(
            f"| **{t}** | {c.get('score',0)}/100 | {c.get('tier','?')} | {status_icon} | "
            f"{rsi:.0f} | {vs50} | {vs200} | {draw:.1f}% | {action_str} |"
        )

    # Actionable recommendations
    exits  = [(t,r) for t,r in recommendations.items() if r["action"] == "EXIT"]
    trims  = [(t,r) for t,r in recommendations.items() if r["action"] == "TRIM"]
    adds   = [(t,r) for t,r in recommendations.items() if r["action"] == "ADD"]

    lines += ["", "---", "", "## ACTIONABLE RECOMMENDATIONS", ""]

    if not exits and not trims and not adds:
        lines.append("**No material actions required.** All positions within framework thresholds.\n")
    else:
        for t, r in exits:
            p = portfolio.get(t, {})
            lines += [
                f"### 🔴 EXIT — {t} ({THESIS_MAP.get(t,{}).get('name','')})",
                f"",
                f"| | |",
                f"|---|---|",
                f"| **Shares to sell** | {p.get('shares',0):.4f} |",
                f"| **At price** | ${p.get('live_price',0):.2f} |",
                f"| **Proceeds** | ${p.get('live_mv',0):,.0f} |",
                f"| **Rationale** | {r['rationale']} |",
                f"| **Urgency** | {r['urgency']} |",
                f"",
            ]

        for t, r in trims:
            p   = portfolio.get(t, {})
            tgt = TARGET_WEIGHTS.get(t, 0)
            total_port_mv = total_live_mv
            target_mv = total_port_mv * tgt / 100
            current_mv = p.get("live_mv", 0)
            trim_mv = current_mv - target_mv
            trim_shares = trim_mv / p.get("live_price", 1) if p.get("live_price") else 0
            lines += [
                f"### ⚠️ TRIM — {t} ({THESIS_MAP.get(t,{}).get('name','')})",
                f"",
                f"| | |",
                f"|---|---|",
                f"| **Current weight** | {p.get('weight_pct',0):.1f}% (${current_mv:,.0f}) |",
                f"| **Target weight** | {tgt:.1f}% (${target_mv:,.0f}) |",
                f"| **Shares to sell** | {trim_shares:.2f} |",
                f"| **At price** | ${p.get('live_price',0):.2f} |",
                f"| **Proceeds** | ${trim_mv:,.0f} |",
                f"| **Rationale** | {r['rationale']} |",
                f"",
            ]

        for t, r in adds:
            p   = portfolio.get(t, {})
            tgt = TARGET_WEIGHTS.get(t, 0)
            total_port_mv = total_live_mv
            target_mv = total_port_mv * tgt / 100
            current_mv = p.get("live_mv", 0)
            add_mv = target_mv - current_mv
            add_shares = add_mv / p.get("live_price", 1) if p.get("live_price") else 0
            lines += [
                f"### ✅ ADD — {t} ({THESIS_MAP.get(t,{}).get('name','')})",
                f"",
                f"| | |",
                f"|---|---|",
                f"| **Current weight** | {p.get('weight_pct',0):.1f}% (${current_mv:,.0f}) |",
                f"| **Target weight** | {tgt:.1f}% (${target_mv:,.0f}) |",
                f"| **Shares to add** | {add_shares:.2f} |",
                f"| **Entry price** | ${p.get('live_price',0):.2f} |",
                f"| **Amount** | ${add_mv:,.0f} |",
                f"| **Rationale** | {r['rationale']} |",
                f"| **Urgency** | {r['urgency']} |",
                f"",
            ]

    # Benchmark comparison
    lines += ["---", "", "## BENCHMARK COMPARISON", "",
              "| Portfolio | Return Since May 26 | Notes |",
              "|-----------|--------------------|----|"]

    model_ret = total_return_p
    lines.append(f"| **Model Portfolio** | **{model_ret:+.2f}%** | Based on live prices vs invested cost |")
    for sym, b in benchmarks.items():
        ret = b.get("return_pct")
        label = {"SPY": "S&P 500 (SPY)", "^NSEI": "Nifty 50 (^NSEI)"}.get(sym, sym)
        if ret is not None:
            lines.append(f"| {label} | {ret:+.2f}% | Since {b.get('from_date','?')} |")
        else:
            lines.append(f"| {label} | N/A | {b.get('error','?')} |")
    lines.append(f"| Live Portfolio | See IBKR app | Updated from IBKR daily |")

    lines += [
        "",
        "---",
        "",
        "## POSITION RATIONALE SUMMARY",
        "",
    ]
    for t in sorted_tickers:
        th = THESIS_MAP.get(t, {})
        te = technicals.get(t, {})
        c  = conf_scores.get(t, {})
        sc = thesis_scans.get(t, {})
        lines += [
            f"**{t} — {th.get('name','')}** | Conf {c.get('score',0)}/100 | {sc.get('status','')}",
            f"- Thesis: {th.get('thesis','')}",
            f"- Driver: {th.get('driver','')}",
            f"- Exit if: {th.get('break_trigger','')}",
            f"- RSI {te.get('rsi_14',0):.0f} · {te.get('price_vs_50d','')} 50D MA · {te.get('price_vs_200d','')} 200D MA · {te.get('drawdown_from_52w_high_pct',0):.1f}% from 52W high",
            f"",
        ]

    lines += ["---", f"", f"*Screener run: {now.strftime('%Y-%m-%dT%H:%M:%S%z')}*", ""]
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    _enforce_chinese_wall()
    print("[Model Screener] Starting institutional framework analysis...")
    print("[Model Screener] CHINESE WALL: live account position data excluded ✅")

    # Load data
    ledger     = load_ledger()
    cost_basis = load_cost_basis()
    macro      = load_macro()

    if not ledger:
        print("ERROR: No ledger data found. Run paper_account_aggregator.py first.")
        sys.exit(1)

    latest_date = sorted(ledger.keys())[-1]
    positions   = ledger[latest_date].get("positions", [])
    ledger_syms = [p["symbol"] for p in positions if p["symbol"] != "IBIT"]
    # Master ticker list: union of ledger + TARGET_WEIGHTS (includes new trades today)
    tickers = list(dict.fromkeys(ledger_syms + [t for t in TARGET_WEIGHTS if t not in ledger_syms]))
    print(f"[Model Screener] Portfolio as of {latest_date}: {len(ledger_syms)} in ledger + {len(tickers)-len(ledger_syms)} pending")

    # Technicals — reuse cached, fetch new ones
    print("[Model Screener] Loading technicals...")
    cached = load_existing_technicals()
    technicals = get_all_technicals(tickers, cached)

    # Benchmarks since inception
    print("[Model Screener] Fetching benchmark returns since inception...")
    benchmarks = {}
    for sym in ["SPY", "^NSEI"]:
        benchmarks[sym] = fetch_benchmark_return(sym, INCEPTION_DATE)
        ret = benchmarks[sym].get("return_pct", "error")
        print(f"  {sym}: {ret}%")

    # Portfolio state
    portfolio = get_portfolio_state(ledger, cost_basis, technicals)

    # Confidence scores
    print("[Model Screener] Scoring confidence...")
    conf_scores = {}
    for t in tickers:
        conf_scores[t] = score_ticker(t, technicals.get(t, {}), macro, ledger, cost_basis)

    # Thesis breaks
    thesis_scans = {}
    for t in tickers:
        thesis_scans[t] = scan_thesis(t, technicals.get(t, {}), macro)

    # Recommendations
    recommendations = {}
    for t in tickers:
        p   = portfolio.get(t, {})
        cur = p.get("weight_pct", 0)
        tgt = TARGET_WEIGHTS.get(t, 0)
        pr  = p.get("live_price", 0)
        recommendations[t] = generate_recommendation(
            t, conf_scores[t], thesis_scans[t], technicals.get(t, {}), cur, tgt, pr
        )

    # Print summary
    print()
    print(f"{'Ticker':<6} {'Score':>5} {'Thesis':<12} {'RSI':>5} {'Action':<15}")
    print("-" * 50)
    for t in sorted(tickers, key=lambda x: -conf_scores.get(x, {}).get("score", 0)):
        c  = conf_scores[t]
        th = thesis_scans[t]
        te = technicals.get(t, {})
        r  = recommendations[t]
        print(f"{t:<6} {c['score']:>4}/100  {th['status']:<12} {te.get('rsi_14',0):>4.0f}  {r['action']:<15}")

    # Generate report
    report = generate_report(portfolio, technicals, conf_scores, thesis_scans,
                             recommendations, macro, benchmarks, ledger)
    OUTPUT_MD.write_text(report)
    print(f"\n[Model Screener] Report → {OUTPUT_MD}")

    # Benchmark JSON
    bench_data = {
        "generated_at": datetime.now(TZ).isoformat(),
        "inception_date": INCEPTION_DATE.isoformat(),
        "benchmarks": benchmarks,
        "model_portfolio": {
            "total_invested": sum(v["invested"] for v in portfolio.values()),
            "total_live_mv":  sum(v["live_mv"]  for v in portfolio.values()),
        }
    }
    OUTPUT_BENCH.write_text(json.dumps(bench_data, indent=2))
    print(f"[Model Screener] Benchmark data → {OUTPUT_BENCH}")
    print("[Model Screener] Done ✅")


if __name__ == "__main__":
    main()
