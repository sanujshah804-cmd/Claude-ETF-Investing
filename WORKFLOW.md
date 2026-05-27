# IBKR Screener — Workflow Reference

**Version:** 3.0 | **Last Updated:** May 27, 2026

---

## Overview

The screener is an 18-step pipeline that runs sequentially. Each step builds on the last. No step can be skipped — the framework validator (Step 16) will block recommendations if any upstream output is missing or stale.

```
Run: python3 scripts/run_screener_workflow.py
```

---

## The 18-Step Pipeline

### DATA COLLECTION (Steps 1–5)

| Step | Script | Output | Notes |
|------|--------|--------|-------|
| 1 | `daily_portfolio_report.py` | `data/positions_YYYYMMDD_HHMMSS.csv` | Pulls IBKR Flex Query XML; parses positions + cash |
| 2 | `bootstrap_research_packs.py` | `data/research_packs/` | Prepares per-ticker context from positions |
| 3 | `market_technicals.py` | `data/latest_market_technicals.json` | 50D/200D MA, RSI-14, 52W high/drawdown from Yahoo |
| 4 | `external_data_enrichment.py` | `data/latest_external_data.json` | Analyst consensus (Finnhub), insider trades (Alpha Vantage), news (NewsAPI) |
| 5 | `macro_dashboard.py` | `data/latest_macro_dashboard.json` | Fed rate, yields, VIX, DXY, Brent, sector ETF returns (FRED + Yahoo) |

### PERFORMANCE TRACKING (Steps 6–12)

| Step | Script | Output | Notes |
|------|--------|--------|-------|
| 6 | `performance_comparison.py` | `data/latest_performance_comparison.json` | Actual NAV vs recommended model vs S&P 500 / Nifty 50 |
| 7 | `recommendations_tracker.py` | `data/latest_recommendation_tracking.json` | Actual allocation vs target; divergence tracking |
| 8 | `capture_performance_snapshot.py` | `data/performance_ledger.json` | Portfolio snapshot (v1, total portfolio) |
| 9 | `performance_ledger_manager_v2.py` | `data/performance_ledger_v2.json` | **Invested capital only** return ledger (excludes cash deposits) |
| 10 | `portfolio_analytics.py` | `data/latest_portfolio_analytics.json` | Annualized returns (1Y/3Y/5Y/10Y), Sharpe ratio, max drawdown, volatility |
| 11 | `portfolio_sector_analysis.py` | `data/latest_portfolio_sectors.json` | Sector weights vs S&P 500 and target allocation |
| 12 | `data_source_health.py` | `data/latest_data_source_health.json` | Freshness report for all data files |

### FRAMEWORK SCORING (Steps 13–16)

| Step | Script | Output | Notes |
|------|--------|--------|-------|
| 13 | `thesis_break_scanner.py` | `data/latest_thesis_breaks.json` | INTACT / WEAKENING / BROKEN per position; specific triggers |
| 14 | `confidence_scorer.py` | `data/latest_confidence_scores.json` | 100-point confidence score per position |
| 15 | `pre_analysis_checklist.py` | `data/pre_analysis_checklist.json` | Full validation of all data sections; gates blockers if invalid |
| 16 | `framework_validator.py` | (exit code) | **Gatekeeper** — exits 1 to block if any rule violated |

### REPORTING (Steps 17–18)

| Step | Script | Output | Notes |
|------|--------|--------|-------|
| 17 | `render_screener_report.py` | `reports/latest_visual_screener.html` | Interactive HTML dashboard |
| 18 | `enhanced_recommendation_builder.py` | `reports/enhanced_recommendations.md` | Final institutional-grade recommendations |

---

## Framework Rules (Enforced at Step 16)

All 6 rules must pass before Step 18 runs:

| Rule | What's Checked | Enforced By |
|------|----------------|-------------|
| **Rule 1** — Research Before Speaking | All 6 data files exist with correct structure | `framework_validator.py` |
| **Rule 2** — Recommendation Change Protocol | Specific quantified triggers per position | `thesis_break_scanner.py` |
| **Rule 3** — Confidence Calibration | Score ≥55 required (or BROKEN thesis overrides) | `confidence_scorer.py` + `framework_validator.py` |
| **Rule 4** — Live Data Verification | All files <24h old | `framework_validator.py` |
| **Rule 5** — Prior Call Audit | Actual vs model vs benchmarks tracked | `performance_comparison.py` |
| **Rule 6** — Materiality Filter | Action must cross threshold (crypto >30% drawdown; others >3pp weight change) | `framework_validator.py` |

---

## Confidence Score Breakdown (100 Points)

| Factor | Max Points | Source |
|--------|-----------|--------|
| Historical data support (3Y+) | 20 | `market_technicals.py` |
| Current valuation | 20 | `external_data_enrichment.py` |
| Technical indicators aligned | 15 | `market_technicals.py` |
| Macro regime supports thesis | 20 | `macro_dashboard.py` |
| Analyst consensus aligned | 10 | `external_data_enrichment.py` |
| No material insider selling | 10 | `external_data_enrichment.py` |
| Low execution risk | 5 | (fixed: all holdings are liquid) |

**Thresholds:**
- <55: **DO NOT RECOMMEND** — automatically blocked
- 55–74: **WATCH ONLY** — not recommended for action
- 75–84: **HIGH CONVICTION** — can recommend
- 85+: **STRONGEST CONVICTION** — core position / high-conviction add

---

## Technical Entry Gates (3 Gates)

All 3 must pass before any new entry is considered:

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| **Trend** | Price above both 50D MA and 200D MA | Confirms bull market structure |
| **RSI** | RSI-14 < 65 (ideally 30–55) | Avoids overbought entries; <30 = oversold opportunity |
| **Macro** | VIX <20, DXY <107, yield curve positive, HY spreads <4% | Only deploy capital in supportive regime |

**Exit triggers:**
- RSI > 75 (distribution zone)
- Price breaks below 200D MA
- Drawdown from 52W high exceeds 30% (crypto) or 20% (speculative)
- Thesis break scanner returns BROKEN status

---

## Running Individual Scripts

### Screen the watchlist (non-held tickers)

```bash
# Screen the configured WATCHLIST array in watchlist_screener.py
python3 scripts/watchlist_screener.py

# Screen specific tickers ad-hoc
python3 scripts/watchlist_screener.py --tickers RKLB ASTS PLTR
```

### Check framework compliance only

```bash
python3 scripts/framework_validator.py
# Exit 0 = all rules pass
# Exit 1 = violations detected (shows exactly which rule failed)
```

### Refresh thesis breaks and confidence scores only

```bash
python3 scripts/thesis_break_scanner.py
python3 scripts/confidence_scorer.py
```

### View latest recommendations

```bash
cat reports/enhanced_recommendations.md
```

### View interactive dashboard

```bash
open reports/latest_visual_screener.html
```

---

## Performance Tracking

### How returns are calculated

Returns are calculated on **invested capital only** (original anchor: $34,573.70 on May 1, 2026).

```
Return = (current_invested_value - anchor_invested_value) / anchor_invested_value
```

Cash additions are tracked in the ledger but do NOT affect the return percentage. This prevents cash infusions from diluting or inflating performance.

### Benchmark comparisons

- **S&P 500 (SPY):** Normalized to same starting value
- **Nifty 50 (^NSEI):** Normalized to same starting value
- **Recommended model:** Applies daily price returns to the recommended target allocation snapshot

All three are calculated in `performance_comparison.py` and stored in `latest_performance_comparison.json`.

---

## Orphaned Scripts (Not in Pipeline)

These scripts exist but are **not called by `run_screener_workflow.py`**. They are available for manual use:

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `generate_institutional_report.py` | Old report generator (replaced by `enhanced_recommendation_builder.py`) | Do not use |
| `framework_loader.py` | Original pre-analysis loader (superseded by `pre_analysis_checklist.py` + `framework_validator.py`) | Do not use |
| `dashboard_automation.py` | Dashboard automation utility | Manual only |
| `dashboard_generator.py` | Dashboard generator | Manual only |
| `data_aggregator.py` | Aggregates data sources | Manual only |
| `per_ticker_analysis.py` | Per-ticker deep dive | Manual only |
| `paper_account_aggregator.py` | IBKR paper account aggregator | Manual only |
| `paper_vs_actual_comparison.py` | Paper vs actual performance | Manual only |
| `ibkr_flex_pull_paper.py` | IBKR Flex pull (paper account) | Manual only |
| `report_template_builder.py` | Report template builder | Manual only |
| `xirr_calculator.py` | XIRR / cash-flow return | Manual only |
| `performance_ledger_manager.py` | Ledger v1 (total portfolio, deprecated) | Superseded by v2 |

---

## Data Files Reference

| File | Generated By | Used By |
|------|-------------|---------|
| `latest_market_technicals.json` | `market_technicals.py` | `thesis_break_scanner.py`, `confidence_scorer.py`, `framework_validator.py` |
| `latest_external_data.json` | `external_data_enrichment.py` | `confidence_scorer.py`, `pre_analysis_checklist.py` |
| `latest_macro_dashboard.json` | `macro_dashboard.py` | `confidence_scorer.py`, `pre_analysis_checklist.py`, `framework_validator.py` |
| `latest_confidence_scores.json` | `confidence_scorer.py` | `framework_validator.py`, `enhanced_recommendation_builder.py` |
| `latest_thesis_breaks.json` | `thesis_break_scanner.py` | `framework_validator.py`, `enhanced_recommendation_builder.py` |
| `latest_performance_comparison.json` | `performance_comparison.py` | `framework_validator.py`, `enhanced_recommendation_builder.py` |
| `latest_recommendation_tracking.json` | `recommendations_tracker.py` | `pre_analysis_checklist.py` |
| `latest_portfolio_analytics.json` | `portfolio_analytics.py` | Reports |
| `latest_portfolio_sectors.json` | `portfolio_sector_analysis.py` | Reports |
| `performance_ledger_v2.json` | `performance_ledger_manager_v2.py` | Performance tracking |
| `pre_analysis_checklist.json` | `pre_analysis_checklist.py` | Reference / audit |
| `latest_data_source_health.json` | `data_source_health.py` | Reference |
| `latest_watchlist_screen.json` | `watchlist_screener.py` | Ad-hoc reference |

---

## Key Configuration

### Environment Variables (`.env` — never commit)

```
IBKR_FLEX_TOKEN=your_flex_token
IBKR_FLEX_QUERY_ID=your_query_id
REPORT_TIMEZONE=Asia/Dubai
```

### Watchlist Configuration

Edit `WATCHLIST` array at the top of `scripts/watchlist_screener.py` to add/remove permanent watch candidates.

### Materiality Thresholds

Defined in `scripts/framework_validator.py`:

| Position type | Threshold | Example |
|--------------|-----------|---------|
| Crypto (IBIT) | >30% drawdown from 52W high | BTC -39.7% → EXIT |
| Commodity (IAU) | >3pp weight change | 18.8% → 12.5% trim = 6.3pp → TRIM |
| Broad market (VOOG, QQQM, etc.) | >3pp weight change | 10.7% → 13.8% add = 3.1pp → ADD |

---

## Review Schedule

| Review type | Frequency | Trigger |
|-------------|-----------|---------|
| Full workflow run | Weekly (Sunday) | Calendar + any BROKEN thesis alert |
| Watchlist screen | Ad-hoc | New thesis / market event |
| Framework validator only | After large market moves | VIX spike, DXY > 107, yield curve inversion |
| Post-earnings review | After each major holding reports | AMZN, GOOG, GEV earnings dates |

**Next scheduled review:** June 8, 2026 (post Q1 earnings cycle)

---

## Troubleshooting

**Framework validator exits with error:**
```
❌ RULE VIOLATIONS DETECTED — Block recommendations
```
→ Check which rule failed. Common causes:
- Data files are stale (>24h) → re-run the specific data step
- Confidence score below threshold → check thesis_breaks and confidence_scores
- Materiality threshold not crossed → check if action crosses the pp threshold

**Script exits with "No positions found":**
→ `daily_portfolio_report.py` failed to pull from IBKR. Check:
1. `.env` file has valid `IBKR_FLEX_TOKEN` and `IBKR_FLEX_QUERY_ID`
2. IBKR Flex Query is configured for OpenPositions + CashReport
3. Network access to IBKR API

**yfinance rate limit:**
→ Add a 2–3 second sleep between tickers or reduce fetch frequency.

---

*This document describes what exists and runs today. For planned enhancements, see the Next Steps section in `CLAUDE.md`.*
