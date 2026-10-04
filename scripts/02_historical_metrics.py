"""
02_historical_metrics.py  -  Nike's key historical metrics and three charts, FY2017-FY2026

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
1. Reads the annual SEC financials table built by 01_download.py and the
   segment / channel revenue table built by 01b_segments_from_10k.py.
2. Reads two extra items straight from the raw SEC company-facts file that the
   earlier scripts did not pull: shareholders' equity (needed for invested
   capital) and income tax expense (needed for the tax rate). Each one keeps its
   receipt (XBRL tag, form, accession number, filed date).
3. Calculates, for each fiscal year:
     revenue growth, gross margin, operating margin, free cash flow,
     FCF margin, effective tax rate, invested capital, and ROIC.
   Every input and every in-between step is a column in the output CSV, so any
   number can be re-done by hand in Excel (project rule 4).
4. Calculates growth by segment and by channel (wholesale vs NIKE Direct).
5. Draws three charts: revenue by segment, margins over time, and NIKE Direct
   vs wholesale.

WHY IT IS BUILT THIS WAY
------------------------
- Definitions (what "free cash flow" and "ROIC" mean) and the tax-rate choice
  live in scripts/assumptions.py, not here (project rule 3).
- Nothing is typed in by hand. Every input is an SEC 10-K number.
- This script only reads data/; it never changes the earlier scripts' files.

HOW TO RUN
----------
    python3 scripts/02_historical_metrics.py
Needs: pandas, openpyxl, matplotlib.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw charts to files, no screen needed
import matplotlib.pyplot as plt
import pandas as pd

import assumptions as A

# ---------------------------------------------------------------------------
# FILE LOCATIONS
# ---------------------------------------------------------------------------
PROJECT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT / "data" / "processed"
RAW = PROJECT / "data" / "raw"
OUTPUT = PROJECT / "output"
CHARTS = PROJECT / "charts"

# Use the newest copy of each input if the download scripts were re-run.
FIN_XLSX = sorted(PROCESSED.glob("nike_financials_and_prices_*.xlsx"))[-1]
SEG_XLSX = PROCESSED / "nke_segment_revenue_10k.xlsx"
FACTS_JSON = sorted(RAW.glob("companyfacts_CIK0000320187_*.json"))[-1]

FY = "Fiscal year (ends May 31)"


# ---------------------------------------------------------------------------
# STEP 1: LOAD THE TABLES THE EARLIER SCRIPTS BUILT
# ---------------------------------------------------------------------------
fin = pd.read_excel(FIN_XLSX, sheet_name="financials_annual")
seg = pd.read_excel(SEG_XLSX, sheet_name="summary")
years = list(fin[FY].astype(int))


# ---------------------------------------------------------------------------
# STEP 2: PULL EQUITY AND TAX EXPENSE FROM THE RAW SEC FILE (with receipts)
# ---------------------------------------------------------------------------
# Same rule as 01_download.py: only 10-K numbers, matched to Nike's fiscal year
# end (May 31), and when several 10-Ks report the same year, the most recently
# filed one wins (it includes any restatement).
facts = json.loads(FACTS_JSON.read_text())["facts"]["us-gaap"]


def pick_10k_value(tag, fiscal_year, duration):
    """Return (value in USD millions, receipt dict) for one tag and fiscal year."""
    end = f"{fiscal_year}-05-31"
    start = f"{fiscal_year - 1}-06-01"
    rows = [
        r for r in facts[tag]["units"]["USD"]
        if r["form"] == "10-K" and r["end"] == end
        # duration items (like tax expense) must cover the full year;
        # instant items (like equity) are a balance on one date, no start.
        and (r.get("start") == start if duration else "start" not in r)
    ]
    best = max(rows, key=lambda r: r["filed"])
    receipt = {
        "fiscal_year": fiscal_year, "xbrl_tag": tag, "form": best["form"],
        "accession_number": best["accn"], "filed": best["filed"],
        "period_end": end, "value_usd_millions": best["val"] / 1e6,
    }
    return best["val"] / 1e6, receipt


receipts = []
equity, tax = [], []
for y in years:
    v, r = pick_10k_value("StockholdersEquity", y, duration=False)
    equity.append(v); receipts.append({**r, "item": "Shareholders' equity"})
    v, r = pick_10k_value("IncomeTaxExpenseBenefit", y, duration=True)
    tax.append(v); receipts.append({**r, "item": "Income tax expense"})

# Operating working capital lines (balances at May 31). The DCF scripts (04, 05, 06)
# all start their forecast from FY2026's operating working capital, so it is built
# once, here. Same tags as the Excel model's Historicals tab (05_excel_dcf_model.py).
NWC_TAGS = {
    "Accounts receivable, net (USD m)": "AccountsReceivableNetCurrent",
    "Inventories (USD m)": "InventoryFinishedGoodsNetOfReserves",
    "Prepaid expenses and other current assets (USD m)": "PrepaidExpenseAndOtherAssetsCurrent",
    "Accounts payable (USD m)": "AccountsPayableCurrent",
    "Accrued liabilities (USD m)": "AccruedLiabilitiesCurrent",
}
nwc_lines = {label: [] for label in NWC_TAGS}
for y in years:
    for label, tag in NWC_TAGS.items():
        v, r = pick_10k_value(tag, y, duration=False)
        nwc_lines[label].append(v); receipts.append({**r, "item": label.replace(" (USD m)", "")})


# ---------------------------------------------------------------------------
# STEP 3: BUILD THE METRICS TABLE, ONE COLUMN PER STEP
# ---------------------------------------------------------------------------
m = pd.DataFrame({FY: years})

# Inputs copied from the SEC table (all USD millions)
m["Revenue (USD m)"] = fin["Revenue (USD millions)"]
m["Gross profit (USD m)"] = fin["Gross profit (USD millions)"]
m["Selling & administrative expense (USD m)"] = fin["Selling & administrative expense (USD millions)"]
m["Operating income = gross profit - S&A (USD m)"] = m["Gross profit (USD m)"] - m["Selling & administrative expense (USD m)"]
m["Operating cash flow (USD m)"] = fin["Operating cash flow (USD millions)"]
m["Capital expenditures (USD m)"] = fin["Capital expenditures (USD millions)"]
m["Income before income taxes (USD m)"] = fin["Income before income taxes (USD millions)"]
m["Income tax expense (USD m)"] = tax
m["Net income (USD m)"] = fin["Net income (USD millions)"]

# Revenue growth: this year's revenue / last year's revenue - 1.
# FY2017 has no prior year in our table, so it is blank.
m["Revenue growth (%)"] = (m["Revenue (USD m)"] / m["Revenue (USD m)"].shift(1) - 1) * 100

# Margins: each profit line as a share of revenue.
m["Gross margin (%) = gross profit / revenue"] = m["Gross profit (USD m)"] / m["Revenue (USD m)"] * 100
m["Operating margin (%) = operating income / revenue"] = (
    m["Operating income = gross profit - S&A (USD m)"] / m["Revenue (USD m)"] * 100)
m["S&A as % of revenue = S&A / revenue"] = m["Selling & administrative expense (USD m)"] / m["Revenue (USD m)"] * 100

# Free cash flow (definition in assumptions.FCF_DEFINITION)
m["Free cash flow = OCF - capex (USD m)"] = m["Operating cash flow (USD m)"] - m["Capital expenditures (USD m)"]
m["FCF margin (%) = FCF / revenue"] = m["Free cash flow = OCF - capex (USD m)"] / m["Revenue (USD m)"] * 100
m["FCF conversion (%) = FCF / net income"] = m["Free cash flow = OCF - capex (USD m)"] / m["Net income (USD m)"] * 100

# Tax rate. Check first: pretax income - tax should equal net income exactly.
m["Check: pretax - tax - net income (USD m, should be 0)"] = (
    m["Income before income taxes (USD m)"] - m["Income tax expense (USD m)"] - m["Net income (USD m)"])
m["Effective tax rate (%) = tax / pretax income"] = m["Income tax expense (USD m)"] / m["Income before income taxes (USD m)"] * 100

# Invested capital (definition in assumptions.ROIC_DEFINITION), year-end balances
assert A.ROIC_INVESTED_CAPITAL_TIMING["value"] == "year_end"
short_term_borrowings = fin["Notes payable / short-term borrowings (USD millions)"]
if A.MISSING_SHORT_TERM_BORROWINGS_AS_ZERO["value"]:
    short_term_borrowings = short_term_borrowings.fillna(0)
m["Long-term debt, non-current (USD m)"] = fin["Long-term debt, non-current (USD millions)"]
m["Current portion of long-term debt (USD m)"] = fin["Current portion of long-term debt (USD millions)"]
m["Notes payable / short-term borrowings (USD m)"] = short_term_borrowings
m["Total debt, excl. leases (USD m)"] = (
    m["Long-term debt, non-current (USD m)"] + m["Current portion of long-term debt (USD m)"]
    + m["Notes payable / short-term borrowings (USD m)"])
m["Shareholders' equity (USD m)"] = equity
m["Cash and equivalents (USD m)"] = fin["Cash and equivalents (USD millions)"]
m["Short-term investments (USD m)"] = fin["Short-term investments (USD millions)"]
m["Invested capital = debt + equity - cash - ST investments (USD m)"] = (
    m["Total debt, excl. leases (USD m)"] + m["Shareholders' equity (USD m)"]
    - m["Cash and equivalents (USD m)"] - m["Short-term investments (USD m)"])

# Operating working capital = receivables + inventories + prepaid - payables - accrued
for label, values in nwc_lines.items():
    m[label] = values
m["Operating working capital = AR + inventories + prepaid - AP - accrued (USD m)"] = (
    m["Accounts receivable, net (USD m)"] + m["Inventories (USD m)"]
    + m["Prepaid expenses and other current assets (USD m)"]
    - m["Accounts payable (USD m)"] - m["Accrued liabilities (USD m)"])
m["Operating working capital as % of revenue"] = (
    m["Operating working capital = AR + inventories + prepaid - AP - accrued (USD m)"] / m["Revenue (USD m)"] * 100)

# NOPAT ("net operating profit after tax") = operating income x (1 - tax rate)
assert A.ROIC_TAX_RATE_METHOD["value"] == "actual_effective_rate_each_year"
actual_rate = m["Effective tax rate (%) = tax / pretax income"] / 100
norm_rate = A.NORMALIZED_TAX_RATE["value"]
op_inc = m["Operating income = gross profit - S&A (USD m)"]
ic = m["Invested capital = debt + equity - cash - ST investments (USD m)"]
m["NOPAT at actual tax rate (USD m)"] = op_inc * (1 - actual_rate)
m["ROIC at actual tax rate (%) = NOPAT / invested capital"] = m["NOPAT at actual tax rate (USD m)"] / ic * 100
m[f"NOPAT at normalized {norm_rate:.0%} tax rate (USD m)"] = op_inc * (1 - norm_rate)
m[f"ROIC at normalized {norm_rate:.0%} tax rate (%)"] = m[f"NOPAT at normalized {norm_rate:.0%} tax rate (USD m)"] / ic * 100

assert (m["Check: pretax - tax - net income (USD m, should be 0)"].abs() < 0.5).all(), "tax check failed"


# ---------------------------------------------------------------------------
# STEP 4: SEGMENT AND CHANNEL GROWTH
# ---------------------------------------------------------------------------
segment_cols = {
    "North America": "North America revenue (USD m)",
    "EMEA": "EMEA revenue (USD m)",
    "Greater China": "Greater China revenue (USD m)",
    "APLA": "APLA revenue (USD m)",
    "Converse": "Converse revenue (USD m)",
    "NIKE Brand wholesale": "NIKE Brand wholesale (USD m)",
    "NIKE Direct": "NIKE Brand direct / NIKE Direct (USD m)",
}
sg = pd.DataFrame({FY: seg[FY].astype(int)})
for name, col in segment_cols.items():
    sg[f"{name} revenue (USD m)"] = seg[col]
    sg[f"{name} growth (%)"] = (seg[col] / seg[col].shift(1) - 1) * 100
sg["NIKE Direct share of NIKE Brand revenue (%)"] = seg[
    "NIKE Direct share of NIKE Brand revenue (%) = direct / Total NIKE Brand"]


# ---------------------------------------------------------------------------
# STEP 5: SAVE EVERYTHING AS CSV
# ---------------------------------------------------------------------------
OUTPUT.mkdir(exist_ok=True)
m.round(2).to_csv(OUTPUT / "02_historical_metrics.csv", index=False)
sg.round(2).to_csv(OUTPUT / "02_segment_and_channel_growth.csv", index=False)
pd.DataFrame(receipts)[["item", "fiscal_year", "value_usd_millions", "xbrl_tag", "form",
                        "accession_number", "filed", "period_end"]].to_csv(
    OUTPUT / "02_extra_sec_inputs_sources.csv", index=False)


# ---------------------------------------------------------------------------
# STEP 6: CHARTS
# ---------------------------------------------------------------------------
# Colors: a colorblind-checked categorical palette (fixed order), gray text.
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white",
})
CHARTS.mkdir(exist_ok=True)
x = sg[FY]
xlabels = [f"FY{str(y)[2:]}" for y in x]
SOURCE = "Source: Nike 10-K filings, SEC EDGAR. Fiscal years end May 31."


def finish(fig, ax, title, subtitle, path, note=SOURCE):
    ax.set_title(subtitle, loc="left", fontsize=9.5, color=INK2, pad=10)
    fig.suptitle(title, x=0.065, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.065, 0.015, note, fontsize=8, color=INK2)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# Chart 1: revenue by segment, stacked bars (USD billions)
fig, ax = plt.subplots(figsize=(9, 5.2))
bottom = pd.Series(0.0, index=sg.index)
for i, name in enumerate(["North America", "EMEA", "Greater China", "APLA", "Converse"]):
    vals = sg[f"{name} revenue (USD m)"] / 1000
    ax.bar(xlabels, vals, bottom=bottom, color=C[i], width=0.68, label=name,
           edgecolor="white", linewidth=1.2)
    bottom += vals
for i, tot in enumerate(seg["Total NIKE, Inc. revenue (USD m)"] / 1000):
    ax.text(i, bottom[i] + 0.6, f"${tot:.1f}B", ha="center", fontsize=8.5, color=INK)
ax.set_ylabel("Revenue (USD billions)")
ax.set_ylim(0, 58)
ax.legend(ncol=5, frameon=False, loc="upper left", fontsize=9)
finish(fig, ax, "Nike revenue by segment, FY2017-FY2026",
       "Stacked bars = segments; label on top = total NIKE, Inc. revenue",
       CHARTS / "02_revenue_by_segment.png",
       SOURCE + " Global Brand Divisions and Corporate (each under $0.11B) are in the total but not drawn.")

# Chart 2: margins over time (%), one axis
fig, ax = plt.subplots(figsize=(9, 5.2))
gm = m["Gross margin (%) = gross profit / revenue"]
om = m["Operating margin (%) = operating income / revenue"]
for s, col, lab in [(gm, C[0], "Gross margin"), (om, C[1], "Operating margin")]:
    ax.plot(xlabels, s, color=col, linewidth=2, marker="o", markersize=5, label=lab)
    for i in sorted({0, int(s.idxmax()), int(s.idxmin()), len(s) - 1}):  # first, high, low, latest only
        ax.annotate(f"{s[i]:.1f}%", (i, s[i]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8.5, color=INK)
    ax.text(len(s) - 0.6, s.iloc[-1], lab, color=INK2, va="center", fontsize=9)
ax.set_ylim(0, 52)
ax.set_xlim(-0.4, len(xlabels) + 0.9)
ax.set_ylabel("% of revenue")
ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
finish(fig, ax, "Nike gross and operating margin, FY2017-FY2026",
       "Operating income = gross profit - selling & administrative expense (Nike reports no operating income line)",
       CHARTS / "02_margins_over_time.png")

# Chart 3: NIKE Direct vs wholesale (USD billions), with Direct share labeled
fig, ax = plt.subplots(figsize=(9, 5.2))
w = 0.36
pos = range(len(xlabels))
ax.bar([p - w / 2 for p in pos], sg["NIKE Brand wholesale revenue (USD m)"] / 1000, width=w,
       color=C[0], label="Wholesale (sold to retailers)", edgecolor="white", linewidth=1)
ax.bar([p + w / 2 for p in pos], sg["NIKE Direct revenue (USD m)"] / 1000, width=w,
       color=C[1], label="NIKE Direct (own stores + digital)", edgecolor="white", linewidth=1)
for p, share, dv in zip(pos, sg["NIKE Direct share of NIKE Brand revenue (%)"], sg["NIKE Direct revenue (USD m)"]):
    ax.text(p + w / 2, dv / 1000 + 0.5, f"{share:.0f}%", ha="center", fontsize=8, color=INK2)
ax.set_xticks(list(pos), xlabels)
ax.set_ylabel("NIKE Brand revenue (USD billions)")
ax.set_ylim(0, 34)
ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
finish(fig, ax, "NIKE Direct vs wholesale, FY2017-FY2026",
       "Label over each Direct bar = Direct's share of NIKE Brand revenue",
       CHARTS / "02_direct_vs_wholesale.png",
       SOURCE + " NIKE Brand only (excludes Converse).")

print(m[[FY, "Revenue growth (%)", "Gross margin (%) = gross profit / revenue",
         "Operating margin (%) = operating income / revenue", "Free cash flow = OCF - capex (USD m)",
         "Effective tax rate (%) = tax / pretax income",
         "Invested capital = debt + equity - cash - ST investments (USD m)",
         "ROIC at actual tax rate (%) = NOPAT / invested capital",
         f"ROIC at normalized {norm_rate:.0%} tax rate (%)"]].round(1).to_string(index=False))
print(sg.round(1).to_string(index=False))
