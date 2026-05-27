# PORTFOLIO SCREENING FRAMEWORK — 6 MANDATORY RULES

**Version:** 3.0  
**Date:** May 25, 2026  
**Status:** Enforced Programmatically

---

## Overview

This document defines the 6 mandatory rules that govern ALL portfolio analysis, recommendations, and performance tracking. Every script in this screener enforces these rules programmatically — violations block recommendations and flag issues clearly.

---

## THE 6 RULES

### RULE 1: Research Before Speaking

**Requirement:** Never make a recommendation without backing it up with live data across:
- **Fundamental:** Valuation metrics (PE, PEG, expense ratios), analyst consensus, insider trades
- **Technical:** 50D/200D moving averages, RSI, support/resistance, price-volume action, trend
- **Macro:** Fed policy, yields, VIX, DXY, geopolitical events, liquidity regime
- **Institutional:** Analyst target prices, rating changes, analyst count

**Implementation:** 
- `framework_loader.py` validates all required data sections exist and are <24 hours old
- If any data is missing or stale, analysis is blocked with clear error message
- Pre-analysis checklist must show ✅ on all 5 items before proceeding

**What This Prevents:**
- Vague recommendations like "buy because sentiment is good"
- Missing technical context (no trend analysis)
- Ignoring macro regime alignment
- Using stale data (>24h old)

---

### RULE 2: Recommendation Change Protocol

**Requirement:** Every recommendation must identify SPECIFIC data triggers that would warrant changing the recommendation.

**Implementation:**
- `thesis_break_scanner.py` identifies primary investment thesis for each position
- For each thesis, identifies specific breakage triggers (quantified thresholds, not vague)
- Status classified as: INTACT | WEAKENING | BROKEN
- Triggers are data-driven, not emotional

**Examples of Good Triggers:**
- ✅ IBIT: "Down >30% from 52W high" (broken thesis trigger)
- ✅ IAU: "Real rates stabilize above 2.0%" (weaken thesis trigger)
- ✅ AMZN: "AWS guidance cut by >5%" (break thesis trigger)

**Examples of Bad Triggers:**
- ❌ "Market sentiment is negative"
- ❌ "I feel this position is weak"
- ❌ "It's been up too much"

**What This Prevents:**
- Recommendation drift without justification
- Emotional decision-making
- Inability to audit "why did you change your mind?"

---

### RULE 3: Confidence Calibration (100-Point Framework)

**Requirement:** All recommendations must be backed by a 100-point confidence score. Scores <55% automatically block recommendations.

**Scoring Framework (Detailed):**

| Category | Max Points | Criteria |
|----------|-----------|----------|
| **Historical Data Support** | 20 | Does 3+ years of historical price/volume behavior support the thesis direction? |
| **Current Valuation** | 20 | Is current valuation attractive for entry/hold? (PE <25, PEG <1.5, or ETF expense <0.15%) |
| **Technical Indicators** | 15 | Are 50D/200D moving averages, RSI, and trends aligned with thesis? |
| **Macro Regime Support** | 20 | Does macro environment (Fed, yields, VIX, DXY, geopolitical) support thesis? |
| **Analyst Consensus** | 10 | Are >10 analysts tracking this? Is consensus aligned with thesis? |
| **No Material Insider Selling** | 10 | Are insiders holding/buying, not selling? Any C-suite exits? |
| **Execution Risk** | 5 | Is position liquid (daily volume >$1M)? Any binary events (earnings, M&A)? |
| **TOTAL** | **100** | |

**Confidence Thresholds:**
- <55%: **DO NOT RECOMMEND** — Block recommendation, wait for better signal
- 55-74%: **WATCH ONLY (Caution)** — Position monitored, only act if triggers fire
- 75-84%: **HIGH CONVICTION** — Recommend hold/trim based on thesis
- 85%+: **STRONGEST CONVICTION** — Core portfolio position, high conviction add/hold

**Implementation:**
- `confidence_scorer.py` calculates score for all portfolio holdings
- Scores output to `latest_confidence_scores.json`
- Recommendations <55% automatically marked "NO RECOMMENDATION"
- Reports show confidence level for every action (not just score)

**What This Prevents:**
- Over-trading on weak signals
- False confidence in thin data
- Inconsistent conviction across portfolio

---

### RULE 4: Live Data Verification

**Requirement:** All data used in recommendations must be <24 hours old. Stale data must be flagged clearly.

**Implementation:**
- `framework_loader.py` checks timestamp on ALL data files:
  - `latest_market_technicals.json` (must be <24h old)
  - `latest_external_data.json` (must be <24h old)
  - `latest_macro_dashboard.json` (must be <24h old)
  - `latest_recommendation_tracking.json` (must be <24h old)
  - `latest_thesis_breaks.json` (must be <24h old)
  - `latest_confidence_scores.json` (must be <24h old)
  - `performance_ledger_v2.json` (must be <24h old)

- If ANY file is >24h old, analysis is blocked and user is informed which file is stale

**Data Sources:**
- **Technicals:** Yahoo Finance API via market_technicals.py (runs daily)
- **External:** Finnhub (analyst consensus), Alpha Vantage (insider trades), NewsAPI (news)
- **Macro:** FRED API (Fed data, yields), Yahoo Finance (VIX, DXY)
- **Portfolio:** IBKR Flex Query XML (daily via daily_portfolio_report.py)

**What This Prevents:**
- Recommendations based on week-old data
- Surprise market moves invalidating analysis
- Stale analyst consensus

---

### RULE 5: Prior Call Audit

**Requirement:** Track performance of all recommendations against actual portfolio performance and benchmark returns.

**Metrics Tracked:**
1. **Actual Portfolio Return (Invested Capital Only):**
   - Based on: Original anchor capital ($34,573.70 as of May 1)
   - Excludes: Cash deposits (tracked separately)
   - Updated: Every screener run

2. **Recommended Model Portfolio Return:**
   - What portfolio would have returned if we followed all recommendations
   - Calculated from: Recommended allocation × actual price changes
   - Updated: Every screener run

3. **S&P 500 YTD Return:**
   - SPY benchmark proxy
   - Updated: Daily from Yahoo Finance

4. **Nifty 50 YTD Return:**
   - ^NSEI benchmark
   - Updated: Daily from Yahoo Finance

**Implementation:**
- `performance_ledger_v2.json` tracks actual invested capital returns
- `latest_performance_comparison.json` compares actual vs model vs benchmarks
- `latest_recommendation_tracking.json` stores which recommendations were made and when
- Reports show: Actual vs Recommended vs S&P 500 vs Nifty 50 side-by-side

**What This Prevents:**
- Making recommendations that historically underperform benchmarks
- Overstating conviction in bad ideas
- Inability to audit "did we actually outperform?"

---

### RULE 6: Materiality Filter

**Requirement:** Only material breakages trigger exit/trim recommendations. Small noise doesn't warrant action.

**Materiality Thresholds:**

| Position | Materiality Threshold | Example |
|----------|---------------------|---------|
| **Crypto (IBIT)** | >30% drawdown from 52W high | Current: -39.7% ✓ MATERIAL |
| **Gold (IAU)** | Price <50D MA + thesis weaken | Current: Below 50D + rates stabilizing ✓ MATERIAL |
| **Broad market (VOOG)** | >3pp underweight vs target | Current: 10.7% vs 13.5% target ✓ MATERIAL |
| **Individual stocks** | >15% reversal from thesis entry or >20% drawdown | Small positions: Noise filter |

**Non-Material Events (Ignore):**
- 2-3% daily volatility (noise)
- Analyst rating changes without price impact
- Short-term sentiment swings
- Single negative news article

**Implementation:**
- `thesis_break_scanner.py` enforces materiality thresholds
- Only flags WEAKENING/BROKEN if threshold is crossed
- Small drifts are noted but don't trigger recommendations

**What This Prevents:**
- Over-trading on daily noise
- Whipsaw exits/entries
- Exhausting cash with small position adjustments

---

## ENFORCEMENT ARCHITECTURE

### Pre-Screener Validation

Every time `run_screener_workflow.py` is invoked:

1. **Data Freshness Check** (Rule 4)
   - Check all 7 JSON files are <24h old
   - If stale: BLOCK and report which files need refresh

2. **Pre-Analysis Checklist** (Rule 1)
   - Macro state: ✅ or ❌
   - Portfolio state: ✅ or ❌
   - Technical data: ✅ or ❌
   - External data: ✅ or ❌
   - Performance tracking: ✅ or ❌
   - If any ❌: BLOCK and explain missing data

3. **Framework Compliance Check** (All 6 rules)
   - Verify confidence_scorer.py ran on all positions
   - Verify thesis_break_scanner.py identified triggers for each position
   - Verify performance_comparison.py fetched benchmarks
   - If any failed: BLOCK and explain

### Per-Recommendation Validation

For each recommendation generated:

1. **Confidence Check** (Rule 3)
   - Score <55%? → "DO NOT RECOMMEND"
   - 55-74%? → "WATCH ONLY"
   - ≥75%? → Proceed with recommendation

2. **Trigger Documentation** (Rule 2)
   - Every recommendation shows specific trigger
   - Trigger must be quantified (e.g., "down >30%")
   - No vague language

3. **Data Sources** (Rule 1)
   - Show which data backed the recommendation
   - Show dates of data collection

4. **Materiality Check** (Rule 6)
   - Action <materiality threshold? → Don't recommend
   - Action ≥materiality threshold? → Recommend

### Post-Recommendation Tracking

After recommendations are made:

1. **Actual vs Model Performance** (Rule 5)
   - Compare actual portfolio return to model portfolio
   - Compare both to S&P 500 and Nifty 50
   - Report in quarterly review

2. **Recommendation Audit Trail** (Rule 2)
   - Store every recommendation with:
     - Date made
     - Confidence score
     - Thesis status
     - Specific trigger that caused recommendation
     - Entry/exit price targets
   - File: `latest_recommendation_tracking.json` (updated every screener run)

---

## PERFORMANCE TARGETS

These rules exist to support achieving **20%+ annualized IRR** with low drawdown.

**Current Performance (as of May 25, 2026):**
- Actual YTD return: **22.79%** (on invested capital)
- Portfolio NAV: **$42,452.00**
- Days in year: 145 (May 1 - May 25)
- Annualized rate: ~57% (on this trajectory)

**Benchmark Context:**
- S&P 500 YTD: TBD (to be fetched from performance_comparison.py)
- Nifty 50 YTD: TBD (to be fetched from performance_comparison.py)

---

## FRAMEWORK COMPLIANCE CHECKLIST

Before approving ANY recommendation, verify:

- [ ] Rule 1: Data sourced from live APIs (not assumptions)
- [ ] Rule 2: Specific breakage trigger identified (quantified)
- [ ] Rule 3: Confidence score ≥55% (or thesis is BROKEN)
- [ ] Rule 4: All data <24 hours old
- [ ] Rule 5: Prior recommendations tracked and audited
- [ ] Rule 6: Action crosses materiality threshold

**If any box is unchecked: Do not recommend. Block and ask for missing data.**

---

## QUESTIONS & CLARIFICATIONS

**Q: What if confidence is 67% but thesis is BROKEN?**
A: Recommend EXIT anyway. Broken thesis overrides confidence (materiality filter applies).

**Q: What if thesis is INTACT but confidence drops to 40%?**
A: "DO NOT RECOMMEND". Hold position but don't add.

**Q: What if I add new cash to the portfolio?**
A: Track it separately. Returns always calculated on original anchor capital base ($34,573.70).

**Q: What if a recommendation worked out but I didn't follow it?**
A: Audit it. Track in "Model vs Actual" performance comparison. This is Rule 5.

**Q: What if a trigger fires but threshold is just barely crossed?**
A: Check materiality threshold. If not material, don't recommend. Track as "WEAKENING" not "BROKEN".

---

## REFERENCES

- `framework_loader.py` — Rule 1 enforcement (data validation)
- `thesis_break_scanner.py` — Rule 2 enforcement (trigger identification)
- `confidence_scorer.py` — Rule 3 enforcement (100-point scoring)
- `framework_loader.py` — Rule 4 enforcement (data freshness)
- `performance_ledger_manager_v2.py` — Rule 5 enforcement (performance tracking)
- `thesis_break_scanner.py` — Rule 6 enforcement (materiality filtering)
- `run_screener_workflow.py` — Master orchestrator (enforces all rules in sequence)

---

**Framework Status:** ✅ Enforced Programmatically  
**Last Updated:** May 25, 2026  
**Compliance Required:** 100% (all 6 rules, all recommendations)
