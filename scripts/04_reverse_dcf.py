"""
04_reverse_dcf.py  -  Reverse DCF: what revenue growth is today's Nike share price assuming?

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
A normal DCF goes:  assumptions -> future cash flows -> value per share.
A reverse DCF runs it backwards: we FIX the value per share at today's market
price and ask which assumption makes the model hit that price.

Here the unknown is Nike's yearly revenue growth over FY2028-FY2031. FY2027 is
fixed at Nike's own guidance (revenue -8%, margin about 5.6%; 8-K of 2026-10-01),
as in every run of the shared model; the forecast covers the same 5 years as the Excel model. Everything else (margin
path, tax, reinvestment, discount rate) comes from scripts/assumptions.py, and
the model itself is the project's one DCF in scripts/dcf_model.py, the same one
the Excel workbook (script 05) and script 06 use. The script:

1. Builds the discount rate (WACC, "weighted average cost of capital"): the
   yearly return investors in Nike's stock and bonds require, blended by how
   much of each Nike has at market value.
2. Reads Nike's latest cash, investments and debt from its most recent SEC
   filing (the Q1 FY2027 10-Q, balance sheet at 2026-08-31).
3. Uses dcf_model.py, which for ANY growth rate builds the 5-year forecast:
       revenue -> operating income -> after-tax operating income (NOPAT)
       -> plus D&A, minus capex, minus extra working capital -> free cash flow (FCFF)
       -> discounted to today -> plus a terminal value for the years after FY2031
       -> enterprise value -> plus cash, minus debt -> equity value per share.
4. Searches for the growth rate where that value per share equals the price
   (bisection: try a low and a high guess, halve the gap until they meet).
5. Saves the full year-by-year forecast at that growth rate, and sensitivity
   tables showing how the implied growth changes with the margin and WACC.

Every intermediate number is saved in output/ (project rule 4).

HOW TO RUN
----------
    python3 scripts/04_reverse_dcf.py
"""

import json
from pathlib import Path

import pandas as pd

import assumptions as A

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"
OUTPUT = PROJECT / "output"

FACTS_JSON = sorted(RAW.glob("companyfacts_CIK0000320187_*.json"))[-1]
METRICS_CSV = OUTPUT / "02_historical_metrics.csv"
FY = "Fiscal year (ends May 31)"


def v(name):
    """Read one assumption's value from assumptions.py."""
    return getattr(A, name)["value"]


# ---------------------------------------------------------------------------
# STEP 1: LATEST BALANCE SHEET AND SHARE COUNT FROM THE NEWEST SEC FILING
# ---------------------------------------------------------------------------
# Find the most recent balance sheet date in any 10-K or 10-Q, then read each
# item at that date from the latest-filed report. Each keeps its receipt.
facts = json.loads(FACTS_JSON.read_text())["facts"]["us-gaap"]
latest_end = max(
    r["end"] for r in facts["CashAndCashEquivalentsAtCarryingValue"]["units"]["USD"]
    if r["form"] in ("10-K", "10-Q"))


def latest_value(tag, unit="USD", duration_start=None):
    rows = [r for r in facts[tag]["units"][unit]
            if r["form"] in ("10-K", "10-Q") and r["end"] == latest_end
            and (r.get("start") == duration_start if duration_start else "start" not in r)]
    if not rows:
        return 0.0, {"xbrl_tag": tag, "note": f"no value at {latest_end}; treated as 0"}
    r = max(rows, key=lambda r: r["filed"])
    return r["val"] / 1e6, {"xbrl_tag": tag, "form": r["form"], "accession_number": r["accn"],
                            "filed": r["filed"], "period_end": r["end"]}


bs_items = [
    ("Cash and equivalents (USD m)", "CashAndCashEquivalentsAtCarryingValue"),
    ("Short-term investments (USD m)", "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent"),
    ("Long-term debt, non-current (USD m)", "LongTermDebtNoncurrent"),
    ("Current portion of long-term debt (USD m)", "LongTermDebtCurrent"),
    ("Notes payable / short-term borrowings (USD m)", "ShortTermBorrowings"),
]
bs, bs_rows = {}, []
for label, tag in bs_items:
    val, receipt = latest_value(tag)
    bs[label] = val
    bs_rows.append({"item": label, "value": val, **receipt})

# Share count: the 10-Q's diluted weighted-average shares for the quarter.
# (Nike tags its period-end share counts only by share class, which the SEC's
# company-facts file leaves out, so the weighted average is the best SEC number
# available here. It differs from the period-end count by well under 1%.)
quarter_start = max(r["start"] for r in facts["WeightedAverageNumberOfDilutedSharesOutstanding"]["units"]["shares"]
                    if r["end"] == latest_end)
shares, receipt = latest_value("WeightedAverageNumberOfDilutedSharesOutstanding", "shares", quarter_start)
bs_rows.append({"item": "Diluted weighted-average shares, latest quarter (millions)", "value": shares, **receipt})

debt = (bs["Long-term debt, non-current (USD m)"] + bs["Current portion of long-term debt (USD m)"]
        + bs["Notes payable / short-term borrowings (USD m)"])
cash = bs["Cash and equivalents (USD m)"] + bs["Short-term investments (USD m)"]
bs_rows += [
    {"item": "Total debt, excl. leases (USD m)", "value": debt, "note": "sum of the three debt lines"},
    {"item": "Cash + short-term investments (USD m)", "value": cash, "note": "sum of the two lines"},
]


# ---------------------------------------------------------------------------
# STEP 2: SAVE THE BALANCE SHEET, THEN LOAD THE SHARED MODEL
# ---------------------------------------------------------------------------
# dcf_model.py reads this file to build the WACC, so it is written first.
OUTPUT.mkdir(exist_ok=True)
pd.DataFrame(bs_rows).to_csv(OUTPUT / "04_latest_balance_sheet_and_shares.csv", index=False)
import dcf_model as D                                    # noqa: E402 (needs the file above)

price = v("SHARE_PRICE")
wacc = D.WACC
wacc_rows = D.wacc_table()


# ---------------------------------------------------------------------------
# STEP 3: SOLVE FOR THE GROWTH RATE THAT MATCHES THE PRICE (target margin 12.5%)
# ---------------------------------------------------------------------------
# D.implied_growth uses bisection: value per share rises with growth, so keep
# halving a [low, high] range toward the side where the model value crosses the price.
g_star, _ = D.implied_growth()
per_share, table, summary = D.run(D.constant(g_star))
summary["Revenue growth every year FY2028-FY2031 (FY2027 at guidance)"] = g_star
summary["Check: value per share - price (USD, should be ~0)"] = per_share - price
zero_growth_value = D.value_per_share(D.constant(0.0))


# ---------------------------------------------------------------------------
# STEP 4: SENSITIVITY TABLES
# ---------------------------------------------------------------------------
margins = [0.08, 0.10, 0.125, 0.15]
rates = [wacc - 0.01, wacc, wacc + 0.01]
growths_grid = [-0.02, 0.0, 0.02, 0.04, 0.06]
sens = pd.DataFrame(
    [[D.implied_growth(m, wacc=r)[0] * 100 for r in rates] for m in margins],
    index=[f"Target operating margin {m:.1%}" for m in margins],
    columns=[f"WACC {r:.2%}" for r in rates],
)
value_grid = pd.DataFrame(
    [[D.value_per_share(D.constant(g), m) for g in growths_grid] for m in margins],
    index=[f"Target operating margin {m:.1%}" for m in margins],
    columns=[f"Growth {g:.0%}/yr" for g in growths_grid],
)


# ---------------------------------------------------------------------------
# STEP 5: SAVE EVERYTHING
# ---------------------------------------------------------------------------
pd.DataFrame(wacc_rows, columns=["item", "value"]).round(4).to_csv(OUTPUT / "04_wacc.csv", index=False)
table.round(4).to_csv(OUTPUT / "04_forecast_at_implied_growth.csv", index=False)
pd.DataFrame(list(summary.items()), columns=["item", "value"]).round(4).to_csv(
    OUTPUT / "04_valuation_summary.csv", index=False)
sens.round(2).to_csv(OUTPUT / "04_sensitivity_implied_growth_pct.csv", index_label="Implied revenue growth (%/yr)")
value_grid.round(2).to_csv(OUTPUT / "04_sensitivity_value_per_share_usd.csv", index_label="Value per share (USD)")

print(f"Balance sheet date used: {latest_end}")
print(pd.DataFrame(wacc_rows, columns=["item", "value"]).round(3).to_string(index=False))
print()
print(pd.DataFrame(list(summary.items()), columns=["item", "value"]).round(3).to_string(index=False))
print(f"\nValue per share at 0% growth, base-case margin: {zero_growth_value:.2f}")
print("\nImplied growth (%/yr):\n", sens.round(2).to_string())
print("\nValue per share (USD):\n", value_grid.round(2).to_string())


# ---------------------------------------------------------------------------
# STEP 6: CHART - value per share vs growth, one line per target margin
# ---------------------------------------------------------------------------
# Where a line crosses the dashed price line is the growth the market implies
# for that margin.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHARTS = PROJECT / "charts"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
blues = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]   # light = low margin, dark = high
growths = [g / 1000 for g in range(-100, 101, 5)]        # -10% to +10% a year
fig, ax = plt.subplots(figsize=(9, 5.2))
for m, col in zip(margins, blues):
    vals = [D.value_per_share(D.constant(g), m) for g in growths]
    ax.plot([g * 100 for g in growths], vals, color=col, linewidth=2)
    ax.text(growths[-1] * 100 + 0.15, vals[-1], f"{m:.1%} margin", color=INK2, va="center", fontsize=9)
    g_m = D.implied_growth(m)[0]
    if g_m == g_m and growths[0] <= g_m <= growths[-1]:      # skip NaN / off-chart
        ax.plot(g_m * 100, price, "o", color=col, markersize=8, markeredgecolor="white", markeredgewidth=2, zorder=3)
        ax.annotate(f"{g_m:.1%}", (g_m * 100, price), textcoords="offset points", xytext=(0, -16),
                    ha="center", fontsize=8.5, color=INK)
ax.axhline(price, color=INK2, linestyle="--", linewidth=1)
ax.text(growths[0] * 100, price + 1.8, f"Share price ${price:.2f} ({v('VALUATION_DATE')})", color=INK2, fontsize=9)
ax.set_xlabel("Revenue growth per year, FY2028-FY2031 (%), after FY2027 at guidance (-8%)", color=INK2)
ax.set_ylabel("Model value per share (USD)", color=INK2)
ax.set_xlim(growths[0] * 100 - 0.3, growths[-1] * 100 + 2.6)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(GRID)
ax.tick_params(colors=INK2)
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
ax.set_title(f"Each line = a different operating margin Nike reaches by FY2031; WACC {wacc:.1%}",
             loc="left", fontsize=9.5, color=INK2, pad=10)
fig.suptitle("What growth does Nike's share price imply?", x=0.065, ha="left", fontsize=13,
             color=INK, fontweight="bold")
fig.text(0.065, 0.005, "Dots mark where each line meets the price = the growth the market implies at that margin. "
         "Source: SEC filings; price and rates from Yahoo.", fontsize=8, color=INK2)
fig.savefig(CHARTS / "04_implied_growth_by_margin.png", dpi=160, bbox_inches="tight")
plt.close(fig)
