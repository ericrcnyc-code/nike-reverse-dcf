# Nike FY2017–FY2026: key metrics and what happened

Built by `scripts/02_historical_metrics.py` from SEC 10-K data. Every number below is in
`output/02_historical_metrics.csv` (company totals) or `output/02_segment_and_channel_growth.csv`
(segments and channels), with each in-between step as its own column. Fiscal years end May 31
(FY2026 = June 2025 to May 2026). Definitions and the tax-rate choice are in `scripts/assumptions.py`.

## The numbers

| FY | Revenue ($B) | Growth | Gross margin | Operating margin | FCF ($B) | ROIC (actual tax) | ROIC (15% tax) |
|---|---|---|---|---|---|---|---|
| 2017 | 34.4 | n/a | 44.6% | 13.8% | 2.7 | 41.1% | 40.2% |
| 2018 | 36.4 | 6.0% | 43.8% | 12.2% | 3.9 | 23.7% | 45.1% |
| 2019 | 39.1 | 7.5% | 44.7% | 12.2% | 4.8 | 51.0% | 51.6% |
| 2020 | 37.4 | -4.4% | 43.4% | 8.3% | 1.4 | 30.7% | 29.7% |
| 2021 | 44.5 | 19.1% | 44.8% | 15.6% | 6.0 | 68.5% | 67.7% |
| 2022 | 46.7 | 4.9% | 46.0% | 14.3% | 4.4 | 51.8% | 48.4% |
| 2023 | 51.2 | 9.6% | 43.5% | 11.5% | 4.9 | 39.4% | 41.0% |
| 2024 | 51.4 | 0.3% | 44.6% | 12.3% | 6.6 | 45.7% | 45.6% |
| 2025 | 46.3 | -9.8% | 42.7% | 8.0% | 3.3 | 25.5% | 26.2% |
| 2026 | 46.4 | 0.2% | 42.9% | 8.2% | 2.2 | 22.0% | 23.4% |

## What each metric tells an investor

**Revenue growth** = this year's revenue ÷ last year's revenue − 1.
It tells you whether more people are buying more Nike product, at higher prices, or both. It is the
starting point of any valuation, because every future profit is a slice of future revenue.
Nike example: FY2025 revenue fell 9.8%, from $51.4B to $46.3B.
Trap: one year can mislead. FY2021's +19.1% looks great, but it was a rebound from a COVID-hit FY2020,
so FY2019 to FY2021 was really about 6.7% a year.

**Gross margin** = gross profit ÷ revenue, where gross profit = revenue − cost of making and shipping the goods.
It tells you pricing power: how much of each dollar of sales is left after paying for the product itself.
Nike example: 42.9% in FY2026 means about 43 cents of every sales dollar is left after the product cost.
Trap: a falling gross margin can come from discounting to clear inventory (a one-time problem) or from
weaker brand demand (a lasting problem). The number alone does not tell you which.

**Operating margin** = operating income ÷ revenue. Nike does not print an operating income line, so
here operating income = gross profit − selling & administrative expense (marketing, staff, stores, tech).
It tells you how much profit the core business makes before interest and taxes.
Nike example: 8.2% in FY2026, down from 12.3% in FY2024.
Trap: costs like marketing and staff do not shrink when sales drop, so a small fall in revenue can cause a
big fall in operating margin. That is called operating deleverage, and it is what happened in FY2025.

**Free cash flow (FCF)** = operating cash flow − capital expenditures (spending on stores, offices, IT).
It is the cash the business actually produces that could be paid to shareholders (dividends, buybacks)
or lenders. A DCF values a company on exactly this number.
Nike example: $2.2B in FY2026, down from $6.6B in FY2024.
Trap: FCF swings with working capital (cash tied up in inventory and unpaid customer bills), so one year
can mislead. Nike's FCF dropped to $1.4B in FY2020 and bounced to $6.0B in FY2021. Look at several years, not one.

**Return on invested capital (ROIC)** = after-tax operating income ÷ invested capital, where
invested capital = debt + shareholders' equity − cash − short-term investments (the money tied up in running the business).
It tells you how much profit each dollar put into the business earns. A company whose ROIC is above its
cost of capital (roughly 8–10% for a company like Nike) creates value when it grows; one below destroys value.
Nike example: FY2026 ROIC 22.0% means each $1 of invested capital earned about 22 cents after tax.
Traps:
- The tax rate. FY2018's actual rate was 55.3% because of a one-time charge from the 2017 US tax law, so the
  actual-rate ROIC (23.7%) understates that year. The 15% normalized column removes that noise.
- Nike's ROIC looks very high (20–68%) partly because invested capital is small: Nike holds about $9B of cash
  and investments, buybacks have shrunk equity, and this definition leaves out about $3.1B of store and
  office leases. Including leases would cut FY2026 ROIC to roughly 18% (my estimate: $3.0B NOPAT ÷ $16.9B).
  Compare Nike's ROIC to itself over time, or to peers using the same definition, rather than to a textbook number.

## What happened (for the memo)

Facts are from the 10-K numbers in this project. Lines marked *context* are widely reported background that
I did not check against the 10-K text here.

- **Eight years of growth, then a reset.** Revenue rose from $34.4B (FY2017) to $51.4B (FY2024), about 6% a year,
  with a COVID dip in FY2020 (−4.4%) and a rebound in FY2021 (+19.1%). Growth stalled in FY2024 (+0.3%),
  revenue fell 9.8% in FY2025, and was flat in FY2026 (+0.2%) at $46.4B, back to roughly the FY2022 level.
- **Nike pushed hard into selling direct, then reversed.** NIKE Direct (its own stores and apps) grew from 28% of
  NIKE Brand revenue in FY2017 to 44% in FY2023–FY2024 ($9.1B to $21.5B). Since then Direct has fallen 17.7% to
  $17.7B (39% share), while wholesale recovered to $27.5B in FY2026 (+6.1%), near its FY2024 high.
  *Context:* Nike publicly shifted back toward wholesale partners after a CEO change in October 2024.
- **Profitability stepped down in FY2025 and has not recovered.** Operating margin fell from 12.3% (FY2024) to 8.0%
  (FY2025) and 8.2% (FY2026), tied with FY2020 as the lowest of the decade. Of the 4.1-point drop from FY2024 to
  FY2026, 1.7 points came from lower gross margin and 2.4 points from selling & administrative costs rising from
  32.3% to 34.7% of revenue. Free cash flow fell from $6.6B to $2.2B and ROIC from 45.7% to 22.0% over the same two years.
- **Greater China and Converse shrank the most.** Greater China peaked at $8.3B in FY2021 and fell 29% to $5.8B in
  FY2026, now smaller than APLA ($6.2B). Converse fell 52% from $2.4B (FY2023) to $1.2B (FY2026). North America,
  the largest segment, returned to growth in FY2026 (+4.8%).

## Files

- `output/02_historical_metrics.csv`: every input, step, and metric by year.
- `output/02_segment_and_channel_growth.csv`: segment and channel revenue and growth.
- `output/02_extra_sec_inputs_sources.csv`: filing receipts for equity and tax expense (pulled from the raw SEC file; the earlier scripts did not include them).
- `charts/02_revenue_by_segment.png`, `charts/02_margins_over_time.png`, `charts/02_direct_vs_wholesale.png`.
