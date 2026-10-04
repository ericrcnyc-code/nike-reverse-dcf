# Nike (NKE) valuation: everything in one place

As of 2026-10-04, valuation date 2026-10-02 (share price $33.87). This page pulls together every result in the project.
Each section names the file with the detail. All figures are nominal (inflation included). The one DCF behind every
number is `scripts/dcf_model.py`, mirrored formula for formula in `output/05_nike_dcf_model.xlsx`, and script 06 checks
that the two agree to the cent. Every input is in `scripts/assumptions.py`, with its source and date.

## 1. The answer

Since 2026-10-04 (Eric's request) every DCF run fixes **FY2027 at Nike's own guidance** (8-K, 2026-10-01): revenue -8%
(midpoint of "high-single digit" decline) and an adjusted operating margin of 5.55% (from adjusted EPS of $1.15-1.35).

| Question | Answer |
|---|---|
| What is Nike worth in the base case? | **$42.17 a share**, 25% above the $33.87 price (was $46.88 before the guidance; the memo's more cautious base is $35.53) |
| What does the $33.87 price assume? | **After the guidance year, about 2.9% revenue growth a year (FY2028-31) and a 10.3% operating margin by FY2031** |
| How far back to "normal Nike" is that? | About 48% of the way from FY2026 (0.2% growth, 8.2% margin) to FY2017-24 (5.9% growth, 12.5% margin) |
| What would a full return to normal be worth? | About $45 a share |
| Lowest value with every harsher input at once | $33.58, 1% below the price |

My reading: from the guided FY2027 trough, the market prices a partial recovery to about a 10% margin, still below
Nike's FY2017-24 record and weaker than its recovery after the 1998-99 slump. That is interpretation; the numbers above
are model results. (Before the guidance was built in, the same question gave 1.7% growth and a 9.3% margin, about 26% of
the way back: the guidance year starts Nike lower, so the price now needs more recovery afterwards.)

## 2. What happened to Nike (`output/02_what_happened.md`)

- Revenue grew from $34.4B (FY2017) to $51.4B (FY2024), then fell 9.8% in FY2025 and was flat in FY2026 at $46.4B.
- Operating margin (gross profit - S&A) fell from 12.3% (FY2024) to 8.0% (FY2025) and 8.2% (FY2026). That was 1.7
  points from lower gross margin and 2.4 points from S&A rising to 34.7% of revenue.
- Free cash flow fell from $6.6B to $2.2B, and ROIC from 45.7% to 22.0%, between FY2024 and FY2026.
- NIKE Direct peaked at 44% of NIKE Brand revenue (FY2023-24) and fell to 39%. Wholesale recovered to $27.5B.
  Greater China is down 29% from its peak, Converse is down 52%, and North America grew 4.8% in FY2026.

## 3. The model and its inputs (`output/05_nike_dcf_model.xlsx`, `output/04_wacc.csv`)

| Input | Value | Source |
|---|---|---|
| Share price | $33.87 | Yahoo close, 2026-10-02 |
| Risk-free rate | 5.28% | 10-year Treasury, 2026-10-02 |
| Beta | 1.09 | 60 monthly returns vs S&P 500 |
| Equity risk premium | **4.09%** | Damodaran, 1 Sep 2026, verified in his data file (was 4.23% at the start of 2026) |
| Cost of equity / after-tax cost of debt | 9.74% / 4.80% | CAPM; risk-free + 0.8% spread, 21% tax |
| **WACC** | **9.07%** | 86% equity, 14% debt (market weights) |
| Revenue growth FY2027-31 | -8%, 3%, 4%, 4%, 4% | FY2027 = Nike's guidance midpoint (8-K, 2026-10-01); later years judgment (FY2016-24 compound growth was 5.9%) |
| Operating margin | 5.55% in FY2027 → 12.5% by FY2031 | FY2027 from guidance (adjusted EPS, 25% tax); target = FY2017-24 average |
| Tax / D&A / capex / working capital | 18% / 1.7% / 2.0% / 11.5% of revenue | Nike FY2017-26 averages (10-Ks) |
| Terminal growth | 2.5% | FY2032 built as a normal 2.5%-growth year |
| Cash, debt, shares | $8.4B, $7.9B (excl. leases), 1,484.2m diluted | 10-Q, 2026-08-31 |

Terminal value is 77% of enterprise value, so the long run drives most of the answer.

## 4. What the price implies (`output/06_implied_growth_and_margin_results.md`, `output/04_reverse_dcf_results.md`)

One price can't pin down two unknowns, so each margin has its own implied growth rate (FY2027 fixed at guidance):

| Operating margin by FY2031 | 8% | 9% | 10% | 12.5% | 15% |
|---|---|---|---|---|---|
| Growth per year FY2028-31 the price implies | 11.1% | 7.1% | 3.7% | -2.9% | -7.9% |

The price mostly pins down the margin: each margin point is worth about $3-4 a share, while at a 12.5% margin going from
0% to 6% growth lifts the value only from $37 to $45. Reaching the margin a year earlier (FY2030) changes the implied
growth by about 0.5 points.

![Heatmap](../charts/06_value_heatmap_growth_x_margin.png)

## 5. Nike's own history, FY1993-FY2026 (`output/06a_*.csv`, from 10-Ks on EDGAR)

- Margin below the price-implied 10.3% in only five of 34 years: FY1998, FY1999, FY2020, FY2025 and FY2026. Growth of 2.9%+
  together with a 10.3%+ margin happened in 24 of 33 years.
- Today's slump is the deepest on record: -9.8% revenue in FY2025 and an 8.0% margin, with no rebound in FY2026.
- Outside shocks recovered fast: FY2010 and COVID took about a year. The slump most like today's (FY1998-99, Nike's own
  brand problems) took 4 years to a new revenue high and 8 years to get the margin back near 15%. In the four years
  after it, Nike still grew 5.1% a year with an 11.0% margin, better than what is priced in now.
- Separately reported one-offs (FY1998-2000 restructuring, FY2009 impairments) lower those years' margins further.
  Since FY2010 such costs sit inside S&A.

## 6. Competitors (`output/06b_*.csv`)

Reported operating margin, and compound growth in each company's own currency:

| Company | Growth per year 2021→2025 | Avg margin 2022-25 | Margin 2025 | Source |
|---|---|---|---|---|
| Nike | -0.2% | 10.0% | 8.2% | SEC 10-K |
| adidas | 4.0% | 4.5% | 8.3% | annual report (non-SEC) |
| Puma | 1.8% | 4.1% | -4.9% | annual report (non-SEC) |
| Lululemon | 15.4% | 20.5% | 19.9% | SEC 10-K |
| Deckers | 14.8% | 21.6% | 23.1% | SEC 10-K |
| On Holding | 42.8% | 9.7% | 12.5% | SEC 20-F |

adidas and Puma figures are read directly from their 2025 annual report pages, saved in `data/raw/competitors/`.
adidas's 2016-19 figures include Reebok and its 2020-25 figures exclude it, so its 2020 growth is left blank.

## 7. What could lower the value (`output/07_valuation_risk_checks.md`)

| Change from the base case ($42.17) | Value per share | Change |
|---|---|---|
| Equity risk premium 5.0% | $37.05 | -$5.13 |
| Terminal growth 2.0% | $39.83 | -$2.35 |
| Tax rate 21% (FY2026 actual was 20.3%) | $40.56 | -$1.62 |
| Equity risk premium 4.23% (start of 2026) | $41.30 | -$0.87 |
| Working capital stays at 12.7% of revenue | $41.79 | -$0.39 |
| Leases ($3.2B) counted as debt, consistently | $42.55 | +$0.37 |
| Risk-free back at its 31 Aug level, 4.76% | $45.86 | +$3.69 |
| ERP 5.0%, tax 21%, working capital 12.7% and terminal growth 2.0% together | $33.58 | -$8.60 |

## 7b. Valuation multiples vs peers (`output/08_peer_multiples.xlsx`, details in `output/08_peer_multiples_results.md`)

Prices on 2026-10-02; last twelve months from each company's latest report (adidas: annual report 2025 + half-year
report 2026, non-SEC; the others SEC filings).

| Company | EV/EBITDA | P/E | Revenue growth, last 12 months | Revenue CAGR, 3 years | Operating margin |
|---|---|---|---|---|---|
| Nike | 11.0x | 16.3x | -1.2% | -3.2% | 8.2% |
| adidas | 10.6x | 18.3x | 6.3% | 3.3% | 8.4% |
| Lululemon | 3.7x | 7.5x | 1.7% | 11.0% | 17.8% |
| Deckers | 7.1x | 10.8x | 7.9% | 14.7% | 22.7% |
| On Holding | 15.7x | 21.7x | 18.5% | 35.1% | 13.8% |
| Under Armour | n.m. (loss) | n.m. (loss) | -3.6% | -5.6% | -2.4% |
| Peer median | 8.8x | 14.5x | 6.3% | 11.0% | 13.8% |

Enterprise value excludes leases and includes adidas's minority interests; adidas's and On's IFRS EBITDA has rent taken
back out so it matches US GAAP.

**What peer multiples say Nike is worth** (`output/08_nike_value_from_peers.csv`)

| Method | Multiple | Value per share | vs $33.87 |
|---|---|---|---|
| Peer median EV/EBITDA | 8.8x | $27.14 | -20% |
| Peer median P/E | 14.5x | $30.28 | -11% |
| Peer median EV/EBITDAR (leases as debt) | 9.1x | $30.10 | -11% |
| Peer range, EV/EBITDA (Lululemon to On) | 3.7x-15.7x | $11.51-$48.04 | |
| DCF base case | implies 13.8x EV/EBITDA, 20.2x P/E | $42.17 | +25% |

The DCF's value needs a multiple on today's profit above every peer but On, which grows 18% a year. The gap is the DCF's
margin recovery (5.55% in FY2027 to 12.5% by FY2031): peers price Nike's current profit, the DCF prices its recovered profit.

## 7c. Data audit (`scripts/09_data_audit.py`, `output/09_data_audit.csv`)

256 checks, no failures (13 values of 0 or under 10 were too small to search for):
- 220 Nike figures for FY2017-FY2026 (revenue, profit lines, cash flow, balance sheet, D&A, diluted shares) found
  next to their row labels in Nike's own 10-K documents, independently of the SEC data API they came from.
- 13 figures from the Q1 FY2027 10-Q (balance sheet, shares, the quarter used in the last-twelve-month figures);
  the diluted share count is within 0.1% of the 1,485.3m shares on the 10-Q cover.
- 11 market inputs (Nike and peer prices, Treasury yield, beta recomputed, Damodaran ERP, exchange rates) match the raw downloads.
- 8 consistency checks: the Excel and Python DCFs agree to the cent; scripts 02, 06b and 08 read the same revenues.
- Re-running scripts 02 to 09 from the raw files rebuilt every output CSV unchanged.

## 7d. Nike's FY2027 guidance and the memo scenarios (`scripts/10_memo_scenarios.py`, `output/10_*.csv`)

Nike's Q1 FY2027 earnings release (8-K, 2026-10-01, saved in `data/raw/8k/`) guides FY2027 revenue down "high-single
digits" and adjusted EPS of $1.15-1.35 (27x at $33.87), which implies an adjusted FY2027 operating margin of about 5.6%
(steps in `output/10_guidance_margin.csv`). Since 2026-10-04 the base case and every reverse DCF use it for FY2027.
Investment memo scenarios (FY2027 at guidance, then each path's margin by FY2031): bear $23.90 (7.5%), memo base $35.53
(10.5%), bull $44.65 (12.5%, faster growth); project base $42.17 (12.5%). With 3/4/4/4% growth after FY2027 the price
needs a 10.0% FY2031 margin. The audit (script 09) checks the guidance figures against the release text.

## 8. Limits to keep in mind

- **FY2027 is set from Nike's guidance, not from our own forecast.** The 5.55% margin is adjusted (before about $0.3B of
  Pace restructuring charges) and rests on reading "high-single digits" as -8% and "mid-20s" tax as 25%. History of the
  FY2027 input: +1% (original), -1.1% (Q1 actual + rest of year flat), -8% and 5.55% (guidance, 2026-10-04).
- adidas's last-twelve-month lease depreciation and lease interest are its 2025 figures (the half-year report doesn't split them out).
- Peer figures rest on each company's own XBRL data (SEC) or report (adidas); unlike Nike's, they were not re-checked line by line against the printed filings.

- The growth path and the 12.5% margin target are judgment, and they drive the base-case value more than any input
  above. The reverse DCF (section 4) avoids them by asking what the price implies instead.
- Nike's figures before FY2008 were never restated for later acquisitions and sales (Converse, Umbro), so growth in
  those years includes some acquisition effect.
- Shares are the quarter's diluted weighted average; the SEC data has no period-end count. The difference is under 1%.
- Peers use different fiscal years. Each is aligned to the calendar year most of its fiscal year falls in.

## Run order

`01_download` → `01b_segments_from_10k` → `02_historical_metrics` → `03_market_inputs` → `04_reverse_dcf` →
`05_excel_dcf_model` → `06a_nike_long_history` → `06_implied_growth_and_margin` → `06b_competitors` →
`07_valuation_risk_checks` → `08_peer_multiples` → `09_data_audit` → `10_memo_scenarios` (all in `scripts/`).
Script 05 needs LibreOffice Calc (`apt-get install libreoffice-calc` in a fresh container).
