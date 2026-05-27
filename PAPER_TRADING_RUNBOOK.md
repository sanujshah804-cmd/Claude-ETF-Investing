# Paper Trading Runbook — Claude ETF Experiment

**Account opened:** 2026-05-26  
**Initial capital:** $42,452.00 (equity $39,042.58 + cash $3,409.42)  
**Target:** 20%+ annualised return (XIRR)  
**Dashboard:** https://sanujshah804-cmd.github.io/Claude-ETF-Investing/  
**Repo:** https://github.com/sanujshah804-cmd/Claude-ETF-Investing  

---

## 1. What This Is

A real-money-equivalent paper trading experiment where Claude (Anthropic AI) manages a 13-position portfolio using the institutional 6-rule screening framework. All positions are held in an IBKR paper account. Daily performance is pulled via Flex Query, processed locally, and published to GitHub Pages automatically.

**Chinese wall with live account:** The paper trading pipeline has zero access to live IBKR credentials. GitHub Actions only stores `IBKR_FLEX_TOKEN_PAPER`, `IBKR_FLEX_QUERY_ID_PAPER`, and `PAPER_ACCOUNT_ID`. Live credentials (`IBKR_FLEX_TOKEN`, `IBKR_FLEX_QUERY_ID`) are never referenced in any paper trading script.

---

## 2. The 4-Script Daily Pipeline

```
ibkr_flex_pull_paper.py          ← Pull Flex XML from IBKR paper account
        ↓
paper_account_aggregator.py      ← Parse XML, compute P&L, update ledger
        ↓
xirr_calculator.py               ← Compute XIRR / total return from ledger
        ↓
dashboard_automation.py          ← Embed data into HTML, write both index files
```

**Input:** `data/paper/ibkr_flex_paper_YYYY-MM-DD.xml` (IBKR API, never committed)  
**Persistent state:** `reports/paper/performance_ledger_paper.json` and `reports/paper/cost_basis_paper.json`  
**Output:** `docs/index.html` and `index.html` (identical, both committed to GitHub)

---

## 3. GitHub Actions Schedule

**File:** `.github/workflows/dashboard-automation.yml`  
**Cron:** `15 11 * * *` = **11:15 UTC = 3:15 PM Dubai (UTC+4)**

The workflow runs these 8 steps daily:
1. Checkout repository
2. Set up Python 3.11
3. Install dependencies (`numpy`, `numpy-financial`, `requests`)
4. Pull IBKR Flex XML (paper account only)
5. Aggregate positions and update ledger
6. Calculate XIRR metrics
7. Generate dashboard HTML with embedded data
8. Commit and push all changed files

**What gets committed each day:**
```
docs/index.html
index.html
reports/paper/performance_ledger_paper.json
reports/paper/dashboard_metrics.json
reports/paper/cost_basis_paper.json
```

**What is NEVER committed:**
```
data/paper/*.xml          ← Raw IBKR Flex XMLs
.env                      ← Live account credentials
.env.paper                ← Paper account credentials (local only)
```

---

## 4. Failure Recovery Procedures

### 4a. Daily trigger didn't run (missed cron)

GitHub Actions can occasionally skip a cron run. **How to detect:**
1. Visit: https://github.com/sanujshah804-cmd/Claude-ETF-Investing/actions
2. Look for today's run at ~11:15 UTC — if absent or showing a ❌

**Recovery — trigger manually:**
1. Go to the Actions tab in the repo
2. Click "Daily Dashboard Automation" in the left sidebar
3. Click "Run workflow" → "Run workflow" (green button)
4. Wait ~2 minutes for completion
5. Hard-refresh the dashboard (Cmd+Shift+R)

**Alternative — run locally:**
```bash
cd "/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing"
python3 scripts/ibkr_flex_pull_paper.py
python3 scripts/paper_account_aggregator.py
python3 scripts/dashboard_automation.py
git add docs/index.html index.html \
  reports/paper/performance_ledger_paper.json \
  reports/paper/dashboard_metrics.json \
  reports/paper/cost_basis_paper.json
git commit -m "📊 Manual dashboard update $(date -u +'%Y-%m-%d %H:%M UTC')"
git push origin main
```

---

### 4b. IBKR Flex API is offline or market holiday

The Flex pull step uses `|| echo "⚠️ Flex pull failed..."` so the pipeline never aborts here.  
**Effect:** The aggregator finds no new XML → skips → XIRR runs on last-known ledger → dashboard republishes with prior data.  
**Dashboard shows:** Same data as yesterday with yesterday's timestamp. This is correct behaviour. No action needed.

**How to verify:** Check the Actions run log — step 4 will show the warning but steps 5–8 will complete successfully.

---

### 4c. XML file is malformed or missing

If the IBKR API returns a corrupt or empty XML:
- `ibkr_flex_pull_paper.py` writes it to `data/paper/` but may have 0 bytes
- `paper_account_aggregator.py` will fail to parse → exits with error
- The workflow continues (step 5 uses `||` graceful fallback)
- XIRR and dashboard steps proceed with last-known ledger data

**Recovery:** Nothing — the next day's pull will get a fresh XML. If this persists >3 days, check IBKR Flex Query configuration.

---

### 4d. Dashboard shows "Loading..." or stale data after automation ran

1. Check Actions ran successfully (step 8 shows "✅ Dashboard pushed to GitHub")
2. Hard-refresh the live URL (Cmd+Shift+R — **not just F5**)
3. Check browser console (F12 → Console tab) for red errors
4. If console shows `DASHBOARD_METRICS is not defined`: the HTML injection failed  
   → Check `dashboard_automation.py` found the insertion point (`window.addEventListener('load', loadDashboard)`)
5. If correct data is in `reports/paper/performance_ledger_paper.json` but dashboard is stale: GitHub Pages cache — wait 2 minutes and hard refresh

---

### 4e. Positions table shows wrong totals (reconciliation failure)

**The invariant that must always hold:**

```
sum(equity positions market_value)
    + cash_value
  = total_market_value             ← shown in "Portfolio Value" metric card
  = table TOTAL row (Market Value)
  = table TOTAL row (Invested)     ← includes cash as a row
```

**How to diagnose:**
1. Open the live dashboard
2. Note the "Portfolio Value" metric card number
3. Scroll to TOTAL row at bottom of Holdings table
4. If `Market Value TOTAL ≠ Portfolio Value`: cash row may be missing or wrong

**What to check in `performance_ledger_paper.json`:**
- Each date entry must have `cash_value` field
- `total_market_value = equity_value + cash_value` must be true
- Run: `python3 -c "import json; d=json.load(open('reports/paper/performance_ledger_paper.json')); [print(k, v['total_market_value'], '=', v['equity_value']+v['cash_value']) for k,v in d.items()]"`

---

### 4f. GitHub Actions secrets missing or wrong

Symptoms: Step 4 fails with authentication error from IBKR API.

**Check secrets are set:**
1. GitHub repo → Settings → Secrets and variables → Actions
2. Required secrets: `IBKR_FLEX_TOKEN_PAPER`, `IBKR_FLEX_QUERY_ID_PAPER`, `PAPER_ACCOUNT_ID`
3. Values are from IBKR paper account Flex Query configuration

**The script handles missing secrets gracefully** (falls back to last-known data), but the pull will silently fail.

---

## 5. Computation Reference

### 5a. Per-Position P&L

```
cost_basis         = price paid per share at first purchase
                     (locked in cost_basis_paper.json, never overwritten)

invested_amount    = quantity × cost_basis

pnl_dollars        = market_value - invested_amount

pnl_pct            = (pnl_dollars / invested_amount) × 100

% portfolio        = position_market_value / total_account_value × 100
```

**Cost basis locking:** The first time a symbol appears in any Flex XML, its market_price is recorded as cost_basis. All future P&L is calculated vs. this original price, regardless of price on any later day.

### 5b. Account-Level Returns

```
total_return_dollars  = total_account_value - INITIAL_INVESTMENT
total_return_pct      = (total_return_dollars / INITIAL_INVESTMENT) × 100

XIRR (Day 1)          = 0.0%  (not meaningful on day of purchase)
XIRR (Day 2+)         = ((total_account_value / INITIAL_INVESTMENT) ^ (365.25 / days_invested) - 1) × 100
```

**Constants:**
- `INITIAL_INVESTMENT = 42452.00` (hardcoded in `xirr_calculator.py` and `paper_account_aggregator.py`)
- `PAPER_ACCOUNT_START_DATE = 2026-05-26`

### 5c. Cash Reconciliation

```
equity_value           = sum of all open position market values
cash_value             = parsed from CashReport/CashBalance[USD] in Flex XML
                         (fallback: EquitySummaryByReportDateInBase.total - equity)
total_account_value    = equity_value + cash_value
```

The CASH row in the Holdings table uses `cash_value` from the ledger snapshot. If `cash_value > 0.005`, it shows as a separate "CASH — USD Cash (Uninvested)" row so the TOTAL footer matches the metric card exactly.

---

## 6. Daily Health Check

After each automation run, verify:

| Check | Where to look | Expected |
|-------|--------------|----------|
| GitHub Action ran | /actions tab | Green ✅ at ~11:15 UTC |
| Dashboard "Last updated" | Footer of dashboard | Today's date |
| Portfolio Value card | Metric card | Matches sum in Holdings TOTAL |
| Holdings TOTAL row | Bottom of table | = Portfolio Value card |
| Number of positions | Holdings table | 13 + CASH row = 14 rows |
| XIRR | Metric card | 0% on Day 1; increases as returns accrue |
| Console errors | F12 → Console | No red errors |
| `performance_ledger_paper.json` | GitHub repo | Has today's date entry |

**Quick browser verification script** (paste in F12 console on live dashboard):
```javascript
console.log('Metrics:', DASHBOARD_METRICS);
const snap = DASHBOARD_LEDGER[Object.keys(DASHBOARD_LEDGER).sort().pop()];
const posTotal = snap.positions.reduce((s,p) => s + p.market_value, 0);
console.log('Equity sum:', posTotal.toFixed(2));
console.log('Cash:', snap.cash_value);
console.log('Total (should equal metric card):', (posTotal + snap.cash_value).toFixed(2));
console.log('Ledger total_market_value:', snap.total_market_value);
```

---

## 7. Adding or Changing Positions (Rebalancing)

When Claude recommends a rebalance:

1. **Execute the trades in IBKR paper account** (buy/sell via the paper account interface)
2. **Wait for next Flex XML pull** (or trigger manually) — no manual script changes needed
3. **New symbols are auto-recorded:** `paper_account_aggregator.py` checks `cost_basis_paper.json` and adds any new symbol with its first-seen market price as cost basis
4. **Exited positions:** They disappear from the next XML → they're no longer in positions → their cost basis remains in `cost_basis_paper.json` (harmless)
5. **Partial sells:** Quantity updates automatically; cost basis stays at original purchase price

**Do NOT manually edit `cost_basis_paper.json` unless correcting an error** — it is the source of truth for all P&L calculations. Editing it changes all historical P&L.

**If you need to correct a cost basis** (e.g., IBKR execution price differed from displayed price):
```bash
# Example: IAU actual fill was 116.522, not 116.50
python3 -c "
import json
cb = json.load(open('reports/paper/cost_basis_paper.json'))
cb['IAU'] = 116.522
json.dump(cb, open('reports/paper/cost_basis_paper.json', 'w'), indent=2)
print('Updated')
"
# Then re-run the pipeline to regenerate the ledger with corrected P&L
```

---

## 8. File Inventory

### Always Committed to Git

| File | Purpose |
|------|---------|
| `docs/index.html` | Dashboard served by GitHub Pages |
| `index.html` | Root copy (GitHub Pages fallback) |
| `dashboard.html` | Source template for automation |
| `reports/paper/performance_ledger_paper.json` | Daily snapshot history |
| `reports/paper/dashboard_metrics.json` | Pre-computed metrics |
| `reports/paper/cost_basis_paper.json` | Locked purchase prices (never overwrite) |
| `scripts/ibkr_flex_pull_paper.py` | IBKR Flex pull script |
| `scripts/paper_account_aggregator.py` | XML parser and ledger updater |
| `scripts/xirr_calculator.py` | XIRR / return calculator |
| `scripts/dashboard_automation.py` | Dashboard generation orchestrator |
| `.github/workflows/dashboard-automation.yml` | GitHub Actions workflow |
| `PAPER_TRADING_RUNBOOK.md` | This file |

### Never Committed to Git

| File/Pattern | Why |
|-------------|-----|
| `.env`, `.env.paper` | IBKR live and paper account credentials |
| `data/paper/*.xml` | Raw IBKR Flex XML (large, sensitive) |
| `__pycache__/`, `*.pyc` | Python cache |

---

## 9. Security Invariants

These must **never** be violated:

1. **No live credentials in paper trading scripts** — `ibkr_flex_pull_paper.py` only reads `IBKR_FLEX_TOKEN_PAPER` and `IBKR_FLEX_QUERY_ID_PAPER`. The variables `IBKR_FLEX_TOKEN` and `IBKR_FLEX_QUERY_ID` (live account) are not referenced anywhere in paper trading scripts.

2. **No account IDs in HTML** — `docs/index.html` and `index.html` contain no account numbers, tokens, or credentials. Only market data (tickers, prices, quantities).

3. **GitHub Actions secrets are encrypted** — The 3 paper account secrets are stored as encrypted GitHub Secrets. They are injected as environment variables only in the step that needs them (Step 4: Flex pull). They are never logged.

4. **View-only public URL** — https://sanujshah804-cmd.github.io/Claude-ETF-Investing/ is read-only. No one can write to it or modify the dashboard. Only commits to `main` by the workflow (or authenticated user) can change it.

5. **XML files are ephemeral** — Even if IBKR Flex XMLs appear in `data/paper/` locally, they cannot reach GitHub because `.gitignore` includes `data/paper/`.

**To audit security at any time:**
```bash
# Confirm no credentials in staged or tracked files
git grep -i "IBKR_FLEX_TOKEN=" -- '*.py' '*.yml' '*.html' '*.json'  # should return nothing
git grep -i "password\|secret\|token=" -- '*.html'  # should return nothing

# Confirm XML files are gitignored
git check-ignore -v data/paper/ibkr_flex_paper_2026-05-26.xml  # should show: data/paper/
```

---

## 10. Running the Full System Locally

### One-time setup

```bash
cd "/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing"
pip install numpy numpy-financial requests

# Create .env.paper (local only, never commit)
cat > .env.paper << 'EOF'
IBKR_FLEX_TOKEN_PAPER=your_token_here
IBKR_FLEX_QUERY_ID_PAPER=your_query_id_here
PAPER_ACCOUNT_ID=your_account_id_here
EOF
```

### Daily manual run

```bash
cd "/Users/sanujpersonal/Downloads/Cowork Playground/projects/IBKR-investing"
python3 scripts/ibkr_flex_pull_paper.py      # Fetches XML from IBKR
python3 scripts/paper_account_aggregator.py  # Parses XML, updates ledger
python3 scripts/dashboard_automation.py      # Generates both HTML files
```

### Verify dashboard locally

```bash
cd docs
python3 -m http.server 8080
# Then open: http://localhost:8080
```

### Push to live

```bash
git add docs/index.html index.html \
  reports/paper/performance_ledger_paper.json \
  reports/paper/dashboard_metrics.json \
  reports/paper/cost_basis_paper.json
git commit -m "📊 Manual dashboard update $(date -u +'%Y-%m-%d %H:%M UTC')"
git push origin main
# Wait 1-2 minutes, then hard-refresh: Cmd+Shift+R
```

---

## 11. Current Portfolio (as of 2026-05-26)

| Ticker | Name | Qty | Cost Basis | Invested | % Portfolio |
|--------|------|-----|-----------|----------|------------|
| IAU | iShares Gold Trust | 45.5 | $116.522 | $5,301.75 | 12.49% |
| EMXC | iShares MSCI EM ex-China | 35.0 | $121.29 | $4,245.15 | 10.00% |
| VOOG | Vanguard S&P 500 Growth | 35.0 | $121.29 | $4,245.15 | 10.00% |
| PPA | Invesco Aerospace & Defense | 33.0 | $122.21 | $4,032.93 | 9.50% |
| SOXX | iShares Semiconductor | 12.0 | $318.47 | $3,821.64 | 9.00% |
| SMIN | iShares MSCI India Small-Cap | 55.0 | $67.1409 | $3,692.75 | 8.70% |
| EWY | iShares MSCI South Korea | 120.0 | $30.42 | $3,650.40 | 8.60% |
| AMZN | Amazon.com | 4.7 | $586.25 | $2,755.38 | 6.49% |
| GOOG | Alphabet (Google) | 4.7 | $586.25 | $2,755.38 | 6.49% |
| QQQM | Invesco NASDAQ 100 (mini) | 37.0 | $48.19 | $1,783.03 | 4.20% |
| GEV | GE Vernova | 27.0 | $47.16 | $1,273.32 | 3.00% |
| IBIT | iShares Bitcoin Trust | 8.0 | $106.13 | $849.04 | 2.00% |
| NBIS | Nebius Group | 27.0 | $23.58 | $636.66 | 1.50% |
| **CASH** | USD Cash (Uninvested) | — | — | $3,409.42 | 8.03% |
| **TOTAL** | | | | **$42,452.00** | **100%** |

---

**Last updated:** 2026-05-27  
**Status:** ✅ Operational — daily automation running
