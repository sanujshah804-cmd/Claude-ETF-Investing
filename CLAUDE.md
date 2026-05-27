# IBKR Investing Screener — Master Configuration

**Location:** `/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing/`

**Status:** Active | **Version:** Framework 3.0 (INSTRUCTIONS.md compliant)

---

## What This Is

This is the **master source of truth** for the IBKR institutional investment screener. It contains:
- All production screening scripts
- Data pipelines for live IBKR, macro, technical, and external data
- Institutional framework enforcement (100-point confidence scoring, thesis break detection, pre-analysis checklist)
- Performance tracking (invested capital only, excluding cash additions)

**Note:** A separate copy exists at `/Users/sanujpersonal/Documents/Codex/2026-05-01/i-want-to-connect-my-codex/`. These operate independently with **Chinese walls** — neither overwrites the other.

---

## Folder Structure

```
IBKR-investing/
├── CLAUDE.md                    ← This file (READ-ONLY — do not edit)
├── README.md                    ← Setup and usage guide
├── scripts/                     ← All Python screening scripts
│   ├── run_screener_workflow.py              ← Master workflow orchestrator
│   ├── framework_loader.py                   ← Pre-analysis checklist validation
│   ├── thesis_break_scanner.py               ← Thesis break detection
│   ├── confidence_scorer.py                  ← 100-point confidence framework
│   ├── generate_institutional_report.py      ← Institutional analysis generator
│   ├── daily_portfolio_report.py             ← IBKR data pull
│   ├── bootstrap_research_packs.py           ← Research pack generation
│   ├── market_technicals.py                  ← Technical analysis (50D/200D, RSI)
│   ├── external_data_enrichment.py           ← Analyst consensus, insider trades
│   ├── macro_dashboard.py                    ← Macro regime classification
│   ├── recommendations_tracker.py            ← Prior calls vs actual
│   ├── capture_performance_snapshot.py       ← Portfolio snapshot (old version)
│   ├── performance_ledger_manager.py         ← Ledger v1
│   ├── performance_ledger_manager_v2.py      ← Ledger v2 (invested capital only)
│   ├── portfolio_analytics.py                ← Returns, Sharpe, volatility
│   ├── portfolio_sector_analysis.py          ← Sector weights vs benchmarks
│   ├── data_source_health.py                 ← Data freshness report
│   └── render_screener_report.py             ← Visual HTML dashboard
├── data/                        ← Input/output data (DO NOT COMMIT IBKR XML files)
│   ├── positions_*.csv                       ← Latest portfolio snapshots
│   ├── latest_market_technicals.json         ← Technical analysis output
│   ├── latest_external_data.json             ← Analyst/insider data
│   ├── latest_macro_dashboard.json           ← Macro regime classification
│   ├── latest_performance_comparison.json    ← Portfolio vs model vs benchmarks
│   ├── performance_ledger.json               ← Ledger v1 (total portfolio)
│   ├── performance_ledger_v2.json            ← Ledger v2 (invested capital only)
│   └── external_data_cache/                  ← Yahoo/SEC data cache (expires weekly)
├── reports/                     ← Generated analysis documents
│   ├── latest_institutional_analysis.md      ← Current institutional framework report
│   ├── latest_portfolio_analytics.md         ← Historical returns/Sharpe
│   ├── latest_portfolio_sectors.md           ← Sector analysis vs benchmarks
│   ├── latest_visual_screener.html           ← Interactive dashboard
│   └── [timestamped backups]                 ← Archival copies
└── .env                         ← IBKR API credentials (NEVER COMMIT)
    ├── IBKR_FLEX_TOKEN         ← Flex query token
    └── IBKR_FLEX_QUERY_ID      ← Flex query ID
```

---

## Key Files to Know

### Framework Enforcement

**framework_loader.py**
- Pre-analysis checklist before any recommendations
- Validates: macro state, portfolio state, technical data, external data, performance tracking
- Exit code 0 = ready, 1 = missing data

**thesis_break_scanner.py**
- Evaluates each position for INTACT / WEAKENING / BROKEN status
- Checks technical signals (50D/200D MA, RSI, drawdown from 52W high)
- Outputs: latest_thesis_breaks.json

**confidence_scorer.py**
- 100-point framework per INSTRUCTIONS.md Rule 3
- Max 20 pts: Historical data support
- Max 20 pts: Current valuation
- Max 15 pts: Technical indicators
- Max 20 pts: Macro regime support
- Max 10 pts: Analyst consensus
- Max 10 pts: No insider selling
- Max 5 pts: Execution risk
- Thresholds: <55% = DO NOT RECOMMEND, 55-74% = WATCH ONLY, 75-84% = HIGH, 85%+ = STRONGEST

**generate_institutional_report.py**
- Orchestrates all framework scripts
- Generates: latest_institutional_analysis.md with full institutional-grade analysis
- Includes: pre-analysis checklist, thesis breaks, confidence scores, recommendations, deployment plan, risk assessment

### Performance Tracking (v2 — Invested Capital Only)

**performance_ledger_manager_v2.py** (NEW)
- Tracks invested capital returns ONLY (excludes cash additions)
- Mechanism:
  - Anchor date: May 1, 2026 ($34,573.70 invested, $10,774.42 YTD deposits)
  - For each snapshot: Calculate returns only on original invested capital
  - If new cash is deposited, it's tracked separately; returns stay based on original capital base
  - Prevents cash infusions from skewing return metrics

**How it works:**
```
Snapshot date: May 25, 2026
Invested value: $42,452
YTD deposits: $10,774.42 (unchanged since May 1)
→ Return: ($42,452 - $34,573.70) / $34,573.70 = 22.79%

If Sanuj adds $5,000 cash on June 1:
Snapshot date: June 1, 2026
Invested value: $42,500 (same as before, no rebalance)
YTD deposits: $15,774.42 (new addition tracked)
→ Return: Still ($42,500 - $34,573.70) / $34,573.70 = 22.98%
   (New cash doesn't change return %)
→ New deposits since anchor: $5,000 (tracked separately)
```

---

## How to Use

### Run Full Screener Workflow

```bash
cd /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing
python3 scripts/run_screener_workflow.py
```

This runs all 12 steps in sequence:
1. daily_portfolio_report.py
2. bootstrap_research_packs.py
3. market_technicals.py
4. external_data_enrichment.py
5. macro_dashboard.py
6. recommendations_tracker.py
7. capture_performance_snapshot.py
8. portfolio_analytics.py
9. portfolio_sector_analysis.py
10. data_source_health.py
11. render_screener_report.py
12. generate_institutional_report.py ← Outputs institutional analysis

### View Latest Institutional Analysis

```bash
cat /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing/reports/latest_institutional_analysis.md
```

### Check Performance (Invested Capital Only)

```bash
cd /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing
python3 scripts/performance_ledger_manager_v2.py
```

### Update Data Only (No Full Workflow)

```bash
cd /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing

# Pull IBKR positions + macro + technicals + external data
python3 scripts/daily_portfolio_report.py
python3 scripts/market_technicals.py
python3 scripts/external_data_enrichment.py
python3 scripts/macro_dashboard.py

# Then run institutional analysis only
python3 scripts/generate_institutional_report.py
```

---

## INSTRUCTIONS.md Compliance

All recommendations now enforce these rules programmatically:

| Rule | Implementation | Enforced By |
|------|-----------------|-------------|
| Rule 1: Research Before Speaking | Live data validation (macro, technical, institutional) | framework_loader.py |
| Rule 2: Recommendation Change Protocol | Specific data triggers identified for each position | thesis_break_scanner.py |
| Rule 3: Confidence Calibration | 100-point framework; <55% = DO NOT RECOMMEND | confidence_scorer.py |
| Rule 4: Live Data Verification | All data must be <24h old; flagged if stale | framework_loader.py |
| Rule 5: Prior Call Audit | Performance tracking shows vs recommended | performance_ledger_manager_v2.py |
| Rule 6: Materiality Filter | Only material breakages trigger exits/trims | thesis_break_scanner.py |

---

## Chinese Walls: Cowork Playground vs Codex

**Cowork Playground** (master):
- Source of truth for all new scripts and updates
- Updated by Claude when improvements are made
- User can make manual edits here

**Codex** (independent copy):
- Can be run independently for quick testing
- Does NOT overwrite Cowork Playground version
- Does NOT receive updates from Cowork Playground automatically

**To sync updates from Cowork Playground to Codex:**
```bash
# Run this manually when you want to copy updates to Codex
cp -r /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing/scripts/* \
      /Users/sanujpersonal/Documents/Codex/2026-05-01/i-want-to-connect-my-codex/scripts/
```

**To use Cowork Playground version (recommended):**
```bash
# Just use this directory; don't manage the Codex copy
cd /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing
python3 scripts/run_screener_workflow.py
```

---

## Environment Setup

Create `.env` file in this directory (DO NOT COMMIT):

```bash
# .env (LOCAL ONLY — NEVER CHECK IN)
IBKR_FLEX_TOKEN=your_flex_token_here
IBKR_FLEX_QUERY_ID=your_query_id_here
REPORT_TIMEZONE=Asia/Dubai
```

Get these from IBKR:
1. Log in to IBKR
2. Account → Settings → API → Flex Queries
3. Create a query that pulls OpenPositions and CashReport
4. Copy Token and Query ID into .env

---

## Key Improvements in This Version

| Previous (Codex) | Now (Cowork) |
|------------------|--------------|
| Performance tracked on total portfolio | **Invested capital only** (v2 ledger) |
| Cash additions skewed return metrics | **Cash tracked separately; returns unaffected** |
| Recommendations without framework validation | **Pre-analysis checklist required** |
| No thesis break detection | **Automated INTACT/WEAKENING/BROKEN scanning** |
| No confidence thresholds | **100-point framework enforced** |

---

## Next Steps (Optional)

1. **Automated trigger alerts** — Email when thesis breaks or confidence scores drop
2. **Real-time monitoring** — Monitor positions continuously, not just on screener runs
3. **Backtesting module** — Validate historical recommendations
4. **Scenario analysis** — Stress test portfolio under market shocks

---

## Support

For questions about:
- **Framework rules:** See INSTRUCTIONS.md in portfolio directory
- **Technical analysis:** Check market_technicals.py and thesis_break_scanner.py
- **Performance metrics:** See performance_ledger_manager_v2.py
- **Data sources:** See data_source_health.py report

---

**Last Updated:** May 25, 2026
**Framework Version:** 3.0 (INSTRUCTIONS.md compliant)
**Ledger Version:** 2.0 (Invested capital only)
