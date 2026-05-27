# IBKR Screener Migration: Cowork Playground Master Setup

**Date:** May 25, 2026  
**Status:** ✅ Complete  
**Framework Version:** 3.0 (INSTRUCTIONS.md compliant)

---

## What Was Done

### 1. ✅ Performance Tracking Fix (Invested Capital Only)

**Problem:**
- Old system tracked total portfolio value including cash
- When cash was added, return % was skewed
- Example: Add $5,000 cash → portfolio looks like it gained +5% just from deposit

**Solution: Performance Ledger v2**
- Tracks INVESTED capital separately from uninvested cash
- Returns always calculated on original anchor capital base ($34,573.70)
- New cash additions are tracked separately without affecting return %

**How it works:**
```
Anchor (May 1, 2026):
  Invested: $34,573.70
  Cash: $9,152.32
  YTD Deposits: $10,774.42

Current (May 25, 2026):
  Invested: $42,452.00
  Cash: $2,437.34
  YTD Deposits: $10,774.42 (no new additions)
  
Return Calculation:
  ($42,452 - $34,573.70) / $34,573.70 = 22.79%
  (Only based on original anchor capital)

If $5,000 cash added (hypothetical):
  YTD Deposits: $15,774.42 (increased)
  Return still: 22.79% + gains from deploying the $5k
  (Cash addition doesn't skew the base return %)
```

**Implementation:**
- Created: `performance_ledger_manager_v2.py`
- Run: `python3 scripts/performance_ledger_manager_v2.py`
- Output: `data/performance_ledger_v2.json`
- Includes tracking of: invested_value, cash, ytd_deposits, new_deposits_since_anchor

---

### 2. ✅ Master Folder Setup (Cowork Playground)

**Created:**
```
/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing/
├── CLAUDE.md                         ← Project instructions
├── README.md                         ← Setup and usage guide  
├── MIGRATION_SUMMARY.md              ← This file
├── .gitignore                        ← Prevents committing credentials
├── scripts/                          ← All 18 Python scripts
│   ├── run_screener_workflow.py      ← Master orchestrator
│   ├── generate_institutional_report.py
│   ├── framework_loader.py
│   ├── thesis_break_scanner.py
│   ├── confidence_scorer.py
│   ├── performance_ledger_manager_v2.py   ← NEW (invested capital only)
│   └── [14 more scripts for data/analytics]
├── data/                             ← Input/output data
│   ├── positions_*.csv               ← Portfolio snapshots
│   ├── ibkr_flex_*.xml               ← IBKR raw data
│   ├── performance_ledger_v2.json    ← Invested capital tracking
│   └── [other data files]
└── reports/                          ← Generated analysis
    ├── latest_institutional_analysis.md
    └── [other reports]
```

**All files copied from Codex:**
- 18 Python scripts (framework + data pipeline)
- Latest position and IBKR XML files
- Performance ledger initialized with anchor values

**Result:** Cowork Playground is now the **master source of truth** for all IBKR screening.

---

### 3. ✅ Documentation Created

**CLAUDE.md** — Project instructions
- File structure and what each directory contains
- How the framework enforcement works
- Rules from INSTRUCTIONS.md and what implements them
- Chinese walls explanation (Cowork vs Codex)

**README.md** — Comprehensive usage guide
- Quick start setup
- How to run full workflow or individual steps
- Explanation of the core framework (pre-analysis, thesis breaks, confidence scoring)
- Performance tracking v2 deep dive
- Troubleshooting guide

**MIGRATION_SUMMARY.md** — This file
- What was changed and why
- How to migrate if you have local modifications
- Quick reference for both locations

---

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Performance Tracking | Total portfolio (skewed by cash) | Invested capital only (v2 ledger) |
| Cash Handling | Inflates return % | Tracked separately, doesn't affect return % |
| Master Location | Scattered between Codex + local | Centralized in Cowork Playground |
| Governance | No clear source of truth | Cowork = master, Codex = independent copy |
| Documentation | Scattered | Comprehensive CLAUDE.md + README.md + This summary |

---

## Chinese Walls: Cowork vs Codex

### Cowork Playground (Master)
**Location:** `/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing/`

✅ Source of truth for all new development  
✅ All improvements/fixes go here first  
✅ Recommended for weekly screener runs  
✅ Version-controlled and documented

**Use this for:**
```bash
cd "/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing"
python3 scripts/run_screener_workflow.py
```

### Codex (Independent Copy)
**Location:** `/Users/sanujpersonal/Documents/Codex/2026-05-01/i-want-to-connect-my-codex/`

✅ Can run independently for testing  
✅ Available for quick experimentation  
✅ Does NOT auto-sync from Cowork  
✅ Does NOT overwrite Cowork files

**To sync updates TO Codex (manual):**
```bash
cp -r /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing/scripts/* \
      /Users/sanujpersonal/Documents/Codex/2026-05-01/i-want-to-connect-my-codex/scripts/
```

**Important:** The two locations are independent. Changes in Cowork do NOT affect Codex, and vice versa.

---

## Performance Ledger v2: Reference

### Initialization
First run creates ledger with anchor values:
```json
{
  "version": "2.0",
  "anchor_date": "2026-05-01",
  "anchor_invested_value": 34573.70,
  "anchor_ytd_deposits": 10774.42375,
  "snapshots": [
    {
      "date": "2026-05-01",
      "invested_value": 34573.70,
      "ytd_deposits": 10774.42375,
      "cash": 0.0,
      "new_deposits_since_anchor": 0.0,
      "invested_return_pct": 0.0,
      "invested_return_usd": 0.0,
      "compounded_invested_return_pct": 0.0,
      "compounded_invested_return_usd": 0.0
    }
  ]
}
```

### Current State (May 25, 2026)
```json
{
  "date": "2026-05-25",
  "invested_value": 42452.00,
  "ytd_deposits": 10774.42375,
  "cash": 2437.34,
  "new_deposits_since_anchor": 0.0,
  "invested_return_pct": 22.79,
  "invested_return_usd": 7878.30,
  "compounded_invested_return_pct": 22.79,
  "compounded_invested_return_usd": 7878.30
}
```

### Testing the v2 Ledger
```bash
cd "/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing"
python3 scripts/performance_ledger_manager_v2.py

# Output:
# Current Snapshot:
#   Invested Value (stocks/ETFs): $42,452.00
#   Cash Balance: $2,437.34
#   YTD Deposits: $10,774.42
#
# Latest Snapshot (2026-05-25):
#   Invested Return (this period): +22.79% (+$7,878.30)
#   Compounded Return (all-time): +22.79% (+$7,878.30)
#   New Deposits Since Anchor: $0.00
```

---

## How to Update Performance Tracking in capture_performance_snapshot.py

The main screener workflow (Step 7: capture_performance_snapshot.py) still uses v1 for now. To integrate v2:

**Option 1: Keep Both**
- v1 in capture_performance_snapshot.py (total portfolio)
- v2 as supplementary metric (invested capital only)
- Report both in institutional analysis

**Option 2: Migrate to v2 Only**
- Update capture_performance_snapshot.py to call v2 logic
- Remove old v1 calculation
- Use v2 as primary metric

**Recommendation:** Option 1 for now
- Keeps existing dashboards intact
- v2 available as reference metric
- Smooth transition without breaking changes

---

## Action Items

### Immediate (Done ✅)
- ✅ Created performance_ledger_manager_v2.py
- ✅ Set up Cowork Playground master folder
- ✅ Copied all scripts (18 Python files)
- ✅ Created CLAUDE.md with project instructions
- ✅ Created README.md with usage guide
- ✅ Initialized performance_ledger_v2.json with correct anchor values
- ✅ Verified v2 ledger runs correctly and shows +22.79% return
- ✅ Created .gitignore to protect credentials and IBKR data

### Optional (Future Enhancements)
- [ ] Integrate v2 ledger into main screener workflow
- [ ] Add automated alerts when thesis breaks or confidence drops
- [ ] Implement backtesting module for prior call validation
- [ ] Add scenario analysis for market shocks

---

## Going Forward

### For Daily/Weekly Screener Runs
```bash
cd "/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing"
python3 scripts/run_screener_workflow.py
cat reports/latest_institutional_analysis.md
```

### For Performance Review
```bash
python3 scripts/performance_ledger_manager_v2.py
```

### For Data Updates Only
```bash
python3 scripts/daily_portfolio_report.py
python3 scripts/market_technicals.py
python3 scripts/external_data_enrichment.py
python3 scripts/macro_dashboard.py
```

### To Sync Updates to Codex (If Needed)
```bash
cp -r /Users/sanujpersonal/Downloads/Cowork\ Playground/projects/IBKR-investing/scripts/* \
      /Users/sanujpersonal/Documents/Codex/2026-05-01/i-want-to-connect-my-codex/scripts/
```

---

## Files Modified/Created

### New Files
- `scripts/performance_ledger_manager_v2.py` — v2 ledger implementation
- `data/performance_ledger_v2.json` — v2 ledger storage
- `CLAUDE.md` — Project instructions
- `README.md` — Usage guide
- `MIGRATION_SUMMARY.md` — This file
- `.gitignore` — Prevents committing credentials/data

### Modified Files
- `scripts/performance_ledger_manager_v2.py` — Fixed return tuple bug
- Both Codex and Cowork versions now have working v2 ledger

### Unchanged (Copied from Codex)
- All 18 framework and data pipeline scripts
- All reports and JSON data files
- IBKR XML snapshots

---

## Support

**For questions about:**
- Framework rules: See `CLAUDE.md` → "Six Rules Enforced Programmatically"
- Performance v2: See `README.md` → "Performance Tracking (v2 — Invested Capital Only)"
- Technical setup: See `README.md` → "Quick Start"
- File structure: See `CLAUDE.md` → "Folder Structure"

---

**Status:** ✅ Complete and tested  
**Next Review:** Post-earnings or on thesis break trigger (June 8, 2026)  
**Framework Version:** 3.0 (INSTRUCTIONS.md compliant)
