# What growth and margin is Nike's $33.87 share price assuming?

Built by `scripts/06a_nike_long_history.py` (Nike FY1993-FY2026 from SEC 10-Ks),
`scripts/06_implied_growth_and_margin.py` (the solver and heatmap) and `scripts/06b_competitors.py` (peers).
The model is the project's one DCF (`scripts/dcf_model.py`), which is also the Excel model
(`output/05_nike_dcf_model.xlsx`). Script 06 checks that the two give the same value to the cent. Valuation date 2026-10-02.

**FY2027 is fixed at Nike's own guidance** in every run (Q1 FY2027 earnings release, 8-K filed 2026-10-01): revenue -8%
and an adjusted operating margin of 5.55% (steps in `output/10_guidance_margin.csv`). The growth found here is for
FY2028-FY2031, and the margin path runs in a straight line from 5.55% in FY2027 to the FY2031 margin. Last updated 2026-10-04.

## The finding

**After the guided FY2027, the current price assumes Nike gets back to about 2.9% revenue growth a year (FY2028-FY2031)
and a 10.3% operating margin by FY2031.** That is about 48% of the way from FY2026 (0.2% growth and an 8.2% margin)
back to its FY2017-FY2024 record: 5.9% compound annual growth and a 12.5% average margin. A full return to that record
after the guidance year would be worth about $45 a share in the same model.

Against Nike's own record since FY1993, 10.3% is a moderate bar for margin. Nike's operating margin was below it in only
five years (FY1998, FY1999, FY2020, FY2025, FY2026), and it had revenue growth of 2.9% or more together with a 10.3%+
margin in 24 of 33 years. Growth is the weak part: with FY2027 at -8%, revenue from FY2026 to FY2031 grows only about
0.6% a year, as weak as Nike's worst five-year stretches (0.8% a year over FY2021-26 and 1.5% over FY1997-2002). So the
price assumes a recovery, but a slow and partial one. My reading is that the market expects the post-1998 kind of
recovery or a weaker one, not the quick post-COVID bounce. That is interpretation, not something the numbers prove.

![Heatmap](../charts/06_value_heatmap_growth_x_margin.png)

## Why one price gives many answers, and which one is headlined

The price is one number and there are two unknowns, so every point on the black line in the heatmap gives exactly
$33.87 (`output/06_iso_price_curve.csv`):

| Operating margin by FY2031 | Growth per year the price implies, FY2028-31 |
|---|---|
| 8% (about the FY2026 level) | 11.1% |
| 9% | 7.1% |
| 10% | 3.7% |
| 12.5% (FY2017-24 average) | -2.9% |
| 15% | -7.9% |

To headline one point, I assumed Nike recovers the same share of the way back on both growth and margin. That is a
choice, not a fact. The table shows the more useful point: **in this model the price mostly pins down the margin.**
At a 10% margin, moving from 0% to 6% growth lifts the value only from $30 to $36. Each extra point of margin is
worth about $3 a share. Whatever growth you believe, the market is pricing a margin of roughly 10%.

## How the solver works

1. **Same model, run backwards.** `dcf_model.py` holds the DCF once: FY2027 at guidance, then revenue at the unknown
   growth and a straight-line margin path from 5.55%, NOPAT at 18% tax, plus D&A (1.7% of revenue), minus capex (2.0%),
   minus extra working capital (11.5% of revenue), discounted at the 9.07% WACC, plus a terminal value. Every input comes from `scripts/assumptions.py`.
2. **Proof that it matches Excel.** At the base-case inputs it gives exactly the workbook's value ($42.1728), checked every run in `output/06_base_case_check.csv`.
   The script stops with an error if they ever differ (`output/06_base_case_check.csv`).
3. **Bisection.** For a given margin, higher growth always gives a higher value. So the solver starts with a growth rate
   that is far too low (-20%) and one that is far too high (+40%), tries the midpoint, and keeps whichever half still
   contains the price. Each round halves the gap. It stops when the value is within $0.001 of $33.87, which takes 12-16
   rounds. This is Excel's Goal Seek, written out so each step can be checked.
4. **Headline pair.** The same bisection runs on "share of the way back to normal" (0 = FY2026, 1 = FY2017-24 record)
   instead of on growth. It lands at 0.48.

The year-by-year forecast at the headline pair is in `output/06_headline_forecast.csv`, so you can check it by hand.

## Compared with Nike's history

Nike's past slumps, from `output/06a_nike_downturns_and_recoveries.csv`. Operating margin here is gross profit minus
S&A, the same definition the DCF uses:

| Slump | Margin before → low | Worst revenue year | New revenue high | Margin back within 1 pt of before |
|---|---|---|---|---|
| FY1994 | 15.8% → 13.6% | -3.6% | FY1995 (1 yr) | FY1996 (2 yrs after the low) |
| FY1998-99 (Asia crisis, brand fatigue) | 15.0% → 9.0% | -8.1% | FY2002 (4 yrs) | FY2006 (8 yrs) |
| FY2010 (financial crisis) | 12.8% → 13.0% | -0.8% | FY2011 (1 yr) | no real margin drop |
| FY2020 (COVID) | 12.2% → 8.3% | -4.4% | FY2021 (1 yr) | FY2021 (1 yr) |
| FY2025-26 (now) | 12.3% → 8.0% | -9.8% | not yet | not yet |

- **Has Nike hit the implied numbers before?** Yes. Growth of 2.9%+ together with a 10.3%+ margin happened in 24 of
  the 33 years on record.
- **How long did recovery take?** It depended on the cause. Shocks from outside (FY2010, COVID) were fixed in a year.
  The one slump that looks like today's, FY1998-99, was about Nike's own products and brand heat. There, it took
  4 years to beat the old revenue peak and 8 years to get the margin back near 15%. Over FY2000-03, the years after that
  slump, revenue grew 5.1% a year and the margin averaged 11.0%. That is better than the 2.9% and 10.3% the price
  implies now, and it started from a 9.0% margin trough, higher than the 5.55% Nike guides for FY2027.
- **One-offs.** In FY1998-2000 and FY2009 Nike showed restructuring and impairment charges on separate lines below
  S&A. Including them (the "as reported" basis in the 06a table), FY1998 falls to 7.7% and FY1999 to 9.2%, and FY2009
  falls to 9.7%. Since FY2010 such costs sit inside S&A, so the two bases are equal.
- **Today's slump is the deepest on record:** the worst revenue drop (-9.8% in FY2025) and the lowest margin before
  one-offs (8.0%), and FY2026 brought no rebound.

## Compared with competitors

From `output/06b_competitors_summary.csv`. All companies are on the same basis: margin = reported operating income
(including one-offs) / revenue, and growth = nominal compound annual growth in each company's own currency. Years
are aligned to the calendar year most of each fiscal year falls in, so Nike FY2026 = 2025.

| Company | Growth per year, 2021→2025 | Avg margin 2022-25 | Latest margin (2025) | Source |
|---|---|---|---|---|
| Nike | -0.2% | 10.0% | 8.2% | SEC 10-K |
| adidas | 4.0% | 4.5% | 8.3% | **non-SEC**: annual report |
| Puma | 1.8% | 4.1% | -4.9% | **non-SEC**: annual report |
| Lululemon | 15.4% | 20.5% | 19.9% | SEC 10-K |
| Deckers (HOKA, UGG) | 14.8% | 21.6% | 23.1% | SEC 10-K |
| On Holding | 42.8% | 9.7% | 12.5% | SEC 20-F (IFRS) |

![Peers](../charts/06b_margin_and_growth_vs_peers.png)

The implied 10.3% margin sits between the two groups. It is above what the big, broad European brands have earned
lately (adidas reached 8.3% in 2025, and Puma lost money), and far below the focused, fast-growing brands (Lululemon
and Deckers at about 20% or more). The implied 2.9% growth is below every peer's 2021-25 rate except Puma's. Put simply, the
market is pricing Nike like a slightly better adidas, not like the premium brand it was through FY2024. That last
sentence is interpretation.

## Weak spots to know about

- **"By 2030" vs FY2031.** The model reaches its margin target in FY2031 (ending May 2031). Reaching it a year earlier,
  by FY2030, changes the implied growth at any margin by at most 0.6 points (`implied_growth_if_margin_reached_by_fy2030`).
- **Discount rate.** One point of WACC moves the implied growth by about 4.5-5.5 points (`output/04_sensitivity_implied_growth_pct.csv`).
  The equity risk premium (4.09%, Damodaran's 1 September 2026 figure) is verified against his data file. The other
  value-lowering risks are measured in `output/07_valuation_risk_checks.md`.
- **adidas and Puma figures** are read directly from each company's 2025 annual report ten-year table:
  [adidas](https://report.adidas-group.com/2025/en/additional-information/ten-year-overview.html) and
  [Puma](https://annual-report.puma.com/2025/en/additional-information/puma-group-development/index.html). The pages were
  saved on 2026-10-04 in `data/raw/competitors/`, and script 06b reads them. adidas's figures are for continuing
  operations: 2016-19 include Reebok and 2020-25 exclude it, so its 2020 growth is left blank. Puma's 2024 includes an
  adjustment for the discontinued PUMA United business.
- **Old Nike figures** (before FY2008) were never restated for later acquisitions and sales (Converse bought in FY2004,
  Umbro in FY2008, both later sold), so growth in those years includes some acquisition effect.
- **Everything is nominal.** Growth rates include inflation, as does the discount rate. With inflation around 2-3%, 2.9%
  nominal growth is roughly flat in real terms. Comparing 1990s growth with today's also mixes different
  inflation rates.
- **SEC access.** www.sec.gov rejects requests whose User-Agent has no e-mail address. Script 06a defaults to the
  placeholder `you@example.com`; set `SEC_USER_AGENT` to your own name and e-mail before re-downloading.

## Files

- Scripts: `06a_nike_long_history.py` → `06_implied_growth_and_margin.py` → `06b_competitors.py` (full run order in the
  [README](../README.md#how-to-run-it)). The guidance-to-margin steps are in `10_memo_scenarios.py`.
  The shared model is `dcf_model.py`, and every setting is in `assumptions.py`.
- Raw: `data/raw/10k_history/` (6 old Nike 10-Ks), `data/raw/competitors/` (SEC company facts for Lululemon, Deckers
  and On; the adidas and Puma pages are downloaded by `scripts/00_get_non_sec_files.py`).
- Output: `output/04_*`, `output/05_*`, `output/06_*.csv`, `output/06a_*.csv`, `output/06b_*.csv`.
- Charts: `charts/04_implied_growth_by_margin.png`, `charts/06_value_heatmap_growth_x_margin.png`, `charts/06b_margin_and_growth_vs_peers.png`.
