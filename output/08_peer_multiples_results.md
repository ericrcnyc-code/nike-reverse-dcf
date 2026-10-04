# Nike vs peers: multiples, checks and what they say Nike is worth

Built by `scripts/08_peer_multiples.py` (2026-10-04). Prices are from 2026-10-02, the same day as the DCF. adidas: Annual Report 2025 + Half Year Reports 2025 and 2026.

## The table

| Company | EV/EBITDA | P/E | Growth, last 12 months | Growth per year, 3 years | Operating margin |
|---|---|---|---|---|---|
| Nike | 11.0x | 16.3x | -1.2% | -3.2% | 8.2% |
| adidas (non-SEC reports) | 10.6x | 18.3x | 6.3% | 3.3% | 8.4% |
| Lululemon | 3.7x | 7.5x | 1.7% | 11.0% | 17.8% |
| Deckers | 7.1x | 10.8x | 7.9% | 14.7% | 22.7% |
| On Holding | 15.7x | 21.7x | 18.5% | 35.1% | 13.8% |
| Under Armour | n.m. (loss) | n.m. (loss) | -3.6% | -5.6% | -2.4% |
| Peer median (excl. Nike) | 8.8x | 14.5x | 6.3% | 11.0% | 13.8% |

## Factors found in the audit (`output/08_peer_checks.csv`)

| Factor | Effect | Status |
|---|---|---|
| adidas minority interests (EUR 395m at 2026-06-30) were missing from its enterprise value | EV/EBITDA 10.5x to 10.6x | **Fixed** in the main table |
| Leases treated as debt for everyone (EV + lease liabilities, over EBITDA + rent) | Nike 11.0x to 10.2x; adidas 10.6x to 9.1x; On 15.7x to 13.7x; Lululemon 3.7x to 3.9x; Deckers about the same | Check only. The ranking does not change |
| adidas without the IFRS lease fix | 10.6x to 8.2x | This shows why the fix matters: without it, adidas looks 22% cheaper than it is on a like-for-like basis |
| On's Swiss-franc profits at the 12-month average rate (1.2608) instead of the 2026-10-02 rate (1.2041) | EV/EBITDA and P/E about 4.5% lower | Check only |
| Under Armour before USD 128m of restructuring and impairment charges | Margin about 0%, EV/EBITDA about 21x | Check only. Still no real profit, so it stays out of the medians |
| adidas used calendar 2025, not the last 12 months | Growth 4.8% to 6.3%, EV/EBITDA 11.0x to 10.6x, P/E 19.3x to 18.3x | **Fixed**: now uses the 2025 and 2026 half-year reports. Lease depreciation and interest stay at their 2025 amounts, because the half-year report doesn't split them out |
| Under Armour class C shares closed 2.5% below class A | Market cap high by up to about 1% | Not adjusted; too small to matter |
| adidas pensions (EUR 84m) are not counted as debt | Less than 0.3% of EV | Not adjusted; recorded in the inputs |

## What the peers say Nike is worth (`output/08_nike_value_from_peers.csv`)

| Method | Multiple | Value per share | vs the $33.87 price |
|---|---|---|---|
| Peer median EV/EBITDA | 8.8x | $27.14 | -20% |
| Peer median P/E | 14.5x | $30.28 | -11% |
| Peer median EV/EBITDAR (leases as debt) | 9.1x | $30.10 | -11% |
| DCF base case (FY2027 at Nike's guidance) | implies 13.8x EV/EBITDA and 20.2x P/E | $42.17 | +25% |

On peer multiples, Nike's trailing profits support a share price of about $27 to $30, a little below the actual price.
The DCF reaches $42.17 only because it assumes Nike's margin climbs from the guided 5.55% in FY2027 to 12.5% by FY2031.
Valued on trailing profit, that means a multiple above every peer except On, which grows 18% a year. Peers price the
profit Nike earns now; the DCF prices the profit it would earn after recovering.

Looking forward makes Nike look more expensive, not less. Nike's FY2027 guidance (adjusted EPS $1.15-1.35, 8-K filed
2026-10-01) puts the stock at about 27x the $1.25 midpoint, almost double the peer median P/E of 14.5x, which on its own
would value Nike at about $18. The peer P/Es are on trailing profit, so this is a rough comparison, but it shows the
price already assumes earnings recover from FY2027.

How the base case moved to $42.17 as the Q1 FY2027 results and guidance were built in is recorded in the
[changelog](../CHANGELOG.md).
