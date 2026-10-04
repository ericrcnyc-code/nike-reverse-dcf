# Open factors that could lower Nike's DCF valuation

Built by `scripts/07_valuation_risk_checks.py`, last updated 2026-10-04. Each check changes one input in the project's
DCF (`scripts/dcf_model.py`), keeps everything else at the base case, and re-runs the model. The test values and their
sources are in `scripts/assumptions.py` under "DOWNSIDE CHECKS". Full table: `output/07_valuation_risk_checks.csv`.

The base case fixes FY2027 at Nike's guidance (revenue -8%, adjusted operating margin 5.55%; 8-K filed 2026-10-01),
then grows revenue 3%, 4%, 4%, 4% with the margin rising in a straight line to 12.5% by FY2031. It uses Damodaran's
latest equity risk premium, 4.09% for 1 September 2026 (verified in `data/raw/damodaran/ERPbymonth.xlsx`), which gives a
9.07% WACC and **$42.17 a share**.

## The answer

**No single open factor brings the value down to the $33.87 price, but all of them together do.** The biggest is the
equity risk premium. With all four value-lowering changes at once, the value is $33.58, 1% below the price.

| Check | WACC | Value per share | Change vs $42.17 | Margin the price implies (base growth path) |
|---|---|---|---|---|
| Base case (ERP 4.09%) | 9.07% | $42.17 | – | 10.0% |
| **ERP 5.0%** | 9.93% | $37.05 | **-$5.13** | 11.4% |
| **Terminal growth 2.0% instead of 2.5%** | 9.07% | $39.83 | **-$2.35** | 10.6% |
| **Tax 21% instead of 18%** | 9.07% | $40.56 | **-$1.62** | 10.4% |
| **ERP 4.23% (Damodaran, start of 2026)** | 9.20% | $41.30 | **-$0.87** | 10.2% |
| **Working capital stays at 12.7% of revenue** | 9.07% | $41.79 | **-$0.39** | 10.1% |
| Leases counted as debt | 8.85% | $42.55 | +$0.37 | 10.0% |
| Risk-free at 31 Aug level, 4.76% | 8.57% | $45.86 | +$3.69 | 9.2% |
| **All value-lowering changes together** (ERP 5.0%, tax 21%, working capital 12.7%, terminal growth 2.0%) | 9.93% | **$33.58** | **-$8.60** | 12.6% |

The last column re-solves the reverse DCF. It shows the FY2031 operating margin the $33.87 price implies if growth
follows the base path (-8%, 3%, 4%, 4%, 4%). A higher number means the market is assuming more, so the stock looks
less cheap.

## What each open factor turned out to be

- **Equity risk premium: the biggest risk, now verified.** Damodaran's data confirms 4.09% for 1 September 2026, the
  figure the base case uses (it was 4.23% at the start of 2026). Over the last 12 months his monthly figure ranged
  from 3.9% to 4.8%. The real risk is a premium above his: at 5.0%, the value falls about $5.13 a share.
- **Risk-free rate.** The 10-year Treasury yield jumped from 4.76% on 31 August to 5.28% on 2 October
  (`data/raw/market_data_...csv`). The base uses the newer, higher rate, so this already works against the value. If
  yields fell back, the value would rise to about $46.
- **Tax rate.** Nike's FY2026 effective rate was 20.3%, above the 18% we assume (the FY2023-26 average), and Nike guides
  to a mid-20s rate for FY2027. At 21% the value drops $1.62.
- **Terminal growth.** 2.0% (inflation only, no real growth) instead of 2.5% cuts $2.35.
- **Working capital.** The base case assumes Nike's working capital falls from 12.7% to 11.5% of revenue. With revenue
  also falling 8%, that frees about $1.0bn in FY2027. If it stays at 12.7%, the release is about $0.5bn and the value
  drops only $0.39.
- **Leases.** Nike has $3.2bn of operating lease liabilities (10-Q, 31 Aug 2026) that the model leaves out of debt.
  Counting them as debt, and taking the interest part of lease cost (at Nike's own 3.6% lease rate, FY2026 10-K) out of
  operating cost in every forecast year, *raises* the value slightly. Leaving them out was not flattering the result.
- **Share count.** We use 1,484.2m diluted shares, the quarter's weighted average, which already includes share
  awards. The SEC data has no period-end count, so I could not test it. It differs by well under 1%.
- **Nike's pre-FY2008 figures not being restated** only affects the history comparisons, not the valuation.

## How to read this

The factors that lower the value are all inputs where we picked the friendlier end of a reasonable range: ERP, tax
and terminal growth. Taking the harsh end of all of them at once brings the model to about today's price. Under those
harsher inputs the price is "right" only if Nike gets back to its full 12.6% margin by FY2031. That is interpretation
built on the model, not a forecast.
