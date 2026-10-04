# output

Results and every intermediate calculation, so each step can be checked by hand or in Excel. Every file here is
rebuilt by the scripts; nothing is edited by hand except the write-ups (`.md`).

**Start here:** [`00_nike_valuation_summary.md`](00_nike_valuation_summary.md), all results on one page.

| Write-up | Covers | Made from |
|---|---|---|
| [`02_what_happened.md`](02_what_happened.md) | Nike's FY2017-26 metrics, what each one means, what went wrong | script 02 |
| [`04_reverse_dcf_results.md`](04_reverse_dcf_results.md) | The reverse DCF: growth the price implies at each margin | scripts 03, 04 |
| [`06_implied_growth_and_margin_results.md`](06_implied_growth_and_margin_results.md) | Growth and margin together, Nike's history since FY1993, competitors | scripts 06a, 06, 06b |
| [`07_valuation_risk_checks.md`](07_valuation_risk_checks.md) | What could lower the value | script 07 |
| [`08_peer_multiples_results.md`](08_peer_multiples_results.md) | EV/EBITDA and P/E against peers | script 08 |

| Files | What they hold |
|---|---|
| `02_*.csv` | Historical metrics FY2017-26 with every in-between column, segment and channel growth, extra SEC inputs and their filings |
| `03_*.csv` | Monthly returns behind the beta, and the beta itself |
| `04_*.csv` | WACC, latest balance sheet and shares, the forecast at the implied growth, sensitivity tables |
| `05_nike_dcf_model.xlsx`, `05_*.csv` | The Excel DCF with live formulas, and its forecast, valuation and sensitivity exported as CSV |
| `06_*.csv` | Excel-vs-Python check, the iso-price curve, the headline pair and its forecast, the value heatmap table |
| `06a_*.csv` | Nike's growth and margins FY1993-FY2026, and its past downturns and recoveries |
| `06b_*.csv` | Competitors' revenue and margins by year, and the summary table |
| `07_valuation_risk_checks.csv` | Each risk check's inputs and result |
| `08_peer_multiples.xlsx`, `08_*.csv` | Peer multiples (Excel with formulas), every input with its source, audit checks, Nike's value from peer multiples |
| `09_data_audit.csv` | All 256 audit checks and their results |
| `10_*.csv` | FY2027 guidance turned into a margin, and the bear / base / bull scenarios with their forecasts |
