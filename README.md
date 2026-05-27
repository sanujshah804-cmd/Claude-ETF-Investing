# Claude ETF Experiment — AI-Managed Paper Portfolio

**Live Dashboard:** https://sanujshah804-cmd.github.io/Claude-ETF-Investing/

A paper trading experiment where Claude (Anthropic AI) manages a diversified 13-position ETF/equity portfolio using an institutional investment framework. Performance is tracked daily and published automatically.

---

## The Experiment

- **Account type:** IBKR Paper Trading (simulated, zero real money at risk)
- **Opening date:** 2026-05-26
- **Starting capital:** $42,452.00
- **Target:** 20%+ annualised return (XIRR)
- **Strategy:** Core ETF holdings + tactical rebalancing guided by 6-rule institutional framework

The portfolio is managed exclusively by Claude AI following a strict screening protocol that requires live data validation, 100-point confidence scoring, thesis-break detection, and materiality thresholds before any recommendation is acted on.

---

## Dashboard

The dashboard at the link above shows:
- **Portfolio Value** — current market value vs. invested capital
- **Total Return** — $ and % since inception
- **XIRR** — annualised return (equivalent yearly rate)
- **Holdings table** — all 13 positions with quantity, invested amount, market value, P&L, and portfolio %

Data updates automatically every day at ~3:15 PM Dubai time (11:15 UTC) via GitHub Actions.

---

## Portfolio Holdings

13-position diversified portfolio spanning:
- Broad market / growth (VOOG, QQQM)
- Emerging markets (EMXC, EWY, SMIN)
- Sector: Technology (SOXX, AMZN, GOOG)
- Sector: Defence & infrastructure (PPA, GEV)
- Alternatives: Gold (IAU), Bitcoin (IBIT)
- Innovation: Nebius AI (NBIS)

---

## How It Works

```
Daily at 11:15 UTC (GitHub Actions):
  1. ibkr_flex_pull_paper.py       ← Fetch positions from IBKR paper account
  2. paper_account_aggregator.py   ← Parse XML, compute P&L, update ledger
  3. xirr_calculator.py            ← Compute XIRR and return metrics
  4. dashboard_automation.py       ← Embed data into HTML, commit to GitHub
  → GitHub Pages serves updated dashboard
```

For operational details, failure recovery procedures, and computation reference, see [PAPER_TRADING_RUNBOOK.md](PAPER_TRADING_RUNBOOK.md).

---

## Disclaimer

This is a simulated paper trading account. No real money is invested. The experiment is for educational and research purposes — to test whether an AI can manage a diversified portfolio to institutional standards.
