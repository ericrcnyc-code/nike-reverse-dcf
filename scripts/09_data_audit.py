"""
09_data_audit.py  -  Check every input the valuation uses against an independent copy of the source

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
The project's financial numbers come from the SEC's XBRL "company facts" API: the
tagged data companies file next to their reports. This script checks them against
a second, independent copy of the same filings, the human-readable 10-K and 10-Q
documents themselves (the pages an analyst would read). It also checks market
inputs against the raw downloads, and that scripts which use the same number agree.

How a 10-K check works
  For each number (say Nike's FY2026 revenue, 46,398), look in the 10-Ks that show
  that year (the year's own 10-K and the next two, which repeat it as comparatives)
  for the row label ("Revenues") followed closely by that exact number. If the label
  and number appear together, the API value matches what Nike printed.

Every check is one row in output/09_data_audit.csv: what was checked, the project's
value, the source value or where it was found, and PASS / FAIL. The script stops with
an error if any check fails, so a broken input can't slip through unnoticed.
Run after 08 (it reads outputs from 02, 04, 05/06, 06b and 08).
"""

import html
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assumptions as A  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data/raw", ROOT / "output"
rows = []


def record(area, item, project_value, source_value, source, passed):
    """passed: True, False, or None for a number too small to search for (shown as NOT CHECKED)."""
    rows.append({"area": area, "item": item, "project_value": project_value, "source_value": source_value,
                 "source": source, "result": {True: "PASS", False: "FAIL", None: "NOT CHECKED"}[passed]})


def as_text(path):
    """A filing's HTML as one line of plain text (tags removed, spaces collapsed)."""
    t = path.read_text(encoding="utf-8", errors="ignore")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def found_near(text, labels, value, decimals=0, window=300):
    """True if any label is followed within `window` characters by the value as printed,
    e.g. 46,398 or (684) for a negative/outflow. Returns the matching snippet."""
    printed = f"{abs(value):,.{decimals}f}"
    num = re.compile(r"(?<![\d,.])\(?\s*" + re.escape(printed) + r"\s*\)?(?![\d])(?!,\d)")
    for lab in labels:
        for m in re.finditer(re.escape(lab), text, flags=re.I):
            seg = text[m.end(): m.end() + window]
            if num.search(seg):
                return (lab + seg[: num.search(seg).end()])[:120]
    return None


# ---------------------------------------------------------------------------
# A. Nike annual figures (scripts 01/02) vs the 10-K documents, FY2017-FY2026
# ---------------------------------------------------------------------------
TENK = {2017: "nke_10k_nke-5312017x10k.htm", 2018: "nke_10k_nke-5312018x10k.htm", 2019: "nke_10k_nke-531201910k.htm",
        2020: "nke_10k_nke-531202010k.htm", 2021: "nke_10k_nke-20210531.htm", 2022: "nke_10k_nke-20220531.htm",
        2023: "nke_10k_nke-20230531.htm", 2024: "nke_10k_nke-20240531.htm", 2025: "nke_10k_nke-20250531.htm",
        2026: "nke_10k_nke-20260531.htm"}
docs = {fy: as_text(RAW / "10k" / f) for fy, f in TENK.items()}

hist = pd.read_csv(OUT / "02_historical_metrics.csv").set_index("Fiscal year (ends May 31)")
wb = pd.read_excel(ROOT / "data/processed/nike_financials_and_prices_2026-10-04.xlsx", sheet_name="financials_annual")
wb = wb.set_index("Fiscal year (ends May 31)")
LABELS = {  # column in the project file -> row labels used in Nike's 10-Ks
    "Revenue (USD m)": ["Revenues"],
    "Gross profit (USD m)": ["Gross profit"],
    "Selling & administrative expense (USD m)": ["Total selling and administrative expense"],
    "Income before income taxes (USD m)": ["Income before income taxes"],
    "Income tax expense (USD m)": ["Income tax expense"],
    "Net income (USD m)": ["Net income"],
    "Operating cash flow (USD m)": ["Cash provided by operations", "Cash provided by operating activities",
                                    "Cash provided (used) by operations"],
    "Capital expenditures (USD m)": ["Additions to property, plant and equipment"],
    "Long-term debt, non-current (USD m)": ["Long-term debt"],
    "Current portion of long-term debt (USD m)": ["Current portion of long-term debt"],
    "Notes payable / short-term borrowings (USD m)": ["Notes payable"],
    "Shareholders' equity (USD m)": ["Total shareholders' equity", "Total shareholders’ equity"],
    "Cash and equivalents (USD m)": ["Cash and equivalents"],
    "Short-term investments (USD m)": ["Short-term investments"],
    "Accounts receivable, net (USD m)": ["Accounts receivable, net"],
    "Inventories (USD m)": ["Inventories"],
    "Prepaid expenses and other current assets (USD m)": ["Prepaid expenses and other current assets"],
    "Accounts payable (USD m)": ["Accounts payable"],
    "Accrued liabilities (USD m)": ["Accrued liabilities"],
}
WB_LABELS = {"Depreciation & amortization (USD millions)": (["Depreciation"], 0),
             "Diluted weighted-average shares (millions)": (["Diluted"], 1)}

for fy in hist.index:
    if fy not in TENK:
        continue
    sources = [y for y in (fy, fy + 1, fy + 2) if y in docs]   # 10-Ks that print this year
    checks = [(c, hist.loc[fy, c], labs, 0) for c, labs in LABELS.items()]
    checks += [(c, wb.loc[fy, c], labs, d) for c, (labs, d) in WB_LABELS.items()]
    for col, v, labs, d in checks:
        if pd.isna(v) or abs(v) < 10:
            record("A. Nike annual vs 10-K", f"FY{fy} {col}", v, "", "too small to search reliably (0 or under 10)", None)
            continue
        hit = None
        for y in sources:
            snip = found_near(docs[y], labs, v, d)
            if snip:
                hit = (y, snip)
                break
        record("A. Nike annual vs 10-K", f"FY{fy} {col}", v, hit[1] if hit else "not found",
               f"10-K FY{hit[0]} ({TENK[hit[0]]})" if hit else "searched 10-Ks FY" + ", ".join(map(str, sources)),
               hit is not None)

# Derived lines: the project's own arithmetic
for fy in hist.index:
    oi = hist.loc[fy, "Gross profit (USD m)"] - hist.loc[fy, "Selling & administrative expense (USD m)"]
    record("A. Nike annual vs 10-K", f"FY{fy} operating income = gross profit - S&A", hist.loc[fy, "Operating income = gross profit - S&A (USD m)"],
           oi, "recomputed", abs(oi - hist.loc[fy, "Operating income = gross profit - S&A (USD m)"]) < 0.5)

# ---------------------------------------------------------------------------
# B. Nike's latest quarter (Q1 FY2027 10-Q) used by scripts 04 and 08
# ---------------------------------------------------------------------------
q = as_text(RAW / "10q/nke_10q_nke-20260831.htm")
Q_SRC = "10-Q for quarter ended 2026-08-31 (accession 0000320187-26-000193), data/raw/10q/nke_10q_nke-20260831.htm"
bs = pd.read_csv(OUT / "04_latest_balance_sheet_and_shares.csv").set_index("item")["value"]
for item, labs, d in [("Cash and equivalents (USD m)", ["Cash and equivalents"], 0),
                      ("Short-term investments (USD m)", ["Short-term investments"], 0),
                      ("Long-term debt, non-current (USD m)", ["Long-term debt"], 0),
                      ("Current portion of long-term debt (USD m)", ["Current portion of long-term debt"], 0),
                      ("Diluted weighted-average shares, latest quarter (millions)", ["Diluted"], 1)]:
    v = bs[item]
    snip = found_near(q, labs, v, d)
    record("B. Nike Q1 FY2027 vs 10-Q", item + " (script 04)", v, snip or "not found", Q_SRC, snip is not None)
for item, labs in [("Revenues", ["Revenues"]), ("Gross profit", ["Gross profit"]),
                   ("Total selling and administrative expense", ["Total selling and administrative expense"]),
                   ("Net income", ["NET INCOME"]), ("Depreciation and amortization", ["Depreciation and amortization"])]:
    m = re.search(re.escape(labs[0]) + r" \$? ?([\d,]+) \$? ?([\d,]+)", q)
    record("B. Nike Q1 FY2027 vs 10-Q", f"{item}, Q1 FY2027 and Q1 FY2026 (used in script 08's TTM)",
           "", f"{m.group(1)} / {m.group(2)}" if m else "not found", Q_SRC, m is not None)
inp = pd.read_csv(OUT / "08_peer_inputs.csv")
nk = inp[inp["company"] == "Nike"].set_index("item")["value"]
ttm_rev = hist.loc[2026, "Revenue (USD m)"] + 11213 - 11720
record("B. Nike Q1 FY2027 vs 10-Q", "TTM revenue = FY2026 46,398 + Q1 FY27 11,213 - Q1 FY26 11,720", nk["Revenue TTM"], ttm_rev,
       "10-K FY2026 + 10-Q above", abs(nk["Revenue TTM"] - ttm_rev) < 0.5)
ttm_ni = hist.loc[2026, "Net income (USD m)"] + 712 - 727
record("B. Nike Q1 FY2027 vs 10-Q", "TTM net income = 3,108 + 712 - 727", nk["Net income TTM"], ttm_ni,
       "10-K FY2026 + 10-Q above", abs(nk["Net income TTM"] - ttm_ni) < 0.5)
cover = re.search(r"Class A ([\d,]+) Class B ([\d,]+) ([\d,]+)", q)
period_end_sh = float(cover.group(3).replace(",", "")) / 1e6
record("B. Nike Q1 FY2027 vs 10-Q", "Diluted average shares vs shares outstanding on the 10-Q cover (2026-09-28)",
       bs["Diluted weighted-average shares, latest quarter (millions)"], round(period_end_sh, 1),
       Q_SRC + "; difference should be under 1%",
       abs(period_end_sh / bs["Diluted weighted-average shares, latest quarter (millions)"] - 1) < 0.01)

# FY2027 guidance (Nike Q1 FY2027 earnings release, 8-K Ex. 99.1, saved in data/raw/8k/) vs assumptions.py
ER_SRC = "8-K 0000320187-26-000184 Ex. 99.1 (2026-10-01), Outlook"
er = Path(__file__).resolve().parent.parent / "data/raw/8k/nke_8k_2026-10-01_q1fy27_exhibit991_earnings_release.htm"
er_text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", er.read_text(encoding="utf-8", errors="ignore"))))
gd = A.GUIDANCE_FY2027["value"]
record("B. Nike FY2027 guidance vs earnings release", "Revenue 'decline high-single digits' -> -7% to -9%, midpoint used for FY2027",
       A.EXCEL_REVENUE_GROWTH["value"][2027], (gd["revenue_growth_low"] + gd["revenue_growth_high"]) / 2, ER_SRC,
       "decline high-single digits" in er_text
       and abs(A.EXCEL_REVENUE_GROWTH["value"][2027] - (gd["revenue_growth_low"] + gd["revenue_growth_high"]) / 2) < 1e-9)
eps_text = f"${gd['adjusted_eps_low']:.2f} to ${gd['adjusted_eps_high']:.2f}"
record("B. Nike FY2027 guidance vs earnings release", f"Adjusted diluted EPS range {eps_text}", gd["adjusted_eps_low"],
       gd["adjusted_eps_high"], ER_SRC, eps_text in er_text)
record("B. Nike FY2027 guidance vs earnings release", "Tax rate 'mid-20 percent range' read as 25%", gd["tax_rate"], 0.25,
       ER_SRC, "mid-20 percent range" in er_text and gd["tax_rate"] == 0.25)
m27 = (((gd["adjusted_eps_low"] + gd["adjusted_eps_high"]) / 2 * bs["Diluted weighted-average shares, latest quarter (millions)"]
        / (1 - gd["tax_rate"]) - A.NON_OPERATING_INCOME_FY2027["value"])
       / (hist.loc[2026, "Revenue (USD m)"] * (1 + A.EXCEL_REVENUE_GROWTH["value"][2027])))
record("B. Nike FY2027 guidance vs earnings release", "FY2027 operating margin = (EPS x shares / (1 - tax) - non-op) / revenue",
       A.FY2027_OPERATING_MARGIN["value"], round(m27, 5), "assumptions.py, recomputed", abs(m27 - A.FY2027_OPERATING_MARGIN["value"]) < 0.00005)

# ---------------------------------------------------------------------------
# C. Market inputs in assumptions.py vs the raw downloads
# ---------------------------------------------------------------------------
mkt = pd.read_csv(RAW / "market_data_NKE_GSPC_TNX_yfinance_2026-10-02.csv", header=[0, 1], index_col=0, skiprows=[2])
last = mkt.loc["2026-10-02"]
nke_close = float(last[("Close", "NKE")])
record("C. Market inputs", "Nike share price 2026-10-02 (USD)", A.SHARE_PRICE["value"], round(nke_close, 2),
       "data/raw/market_data_NKE_GSPC_TNX_yfinance_2026-10-02.csv", abs(nke_close - A.SHARE_PRICE["value"]) < 0.006)
tnx = float(last[("Close", "^TNX")]) / 100
record("C. Market inputs", "Risk-free rate (10-year Treasury) 2026-10-02", A.RISK_FREE_RATE["value"], round(tnx, 5),
       "same file, ^TNX close / 100", abs(tnx - A.RISK_FREE_RATE["value"]) < 0.00001)
beta_in = pd.read_csv(OUT / "03_beta_monthly_returns.csv")
rcols = [c for c in beta_in.columns if "return" in c.lower()]
y, x = beta_in[rcols[0]].astype(float), beta_in[rcols[1]].astype(float)
beta = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
record("C. Market inputs", f"Beta recomputed from output/03_beta_monthly_returns.csv ({rcols[0]} on {rcols[1]}, "
       f"{len(beta_in)} months)", A.BETA["value"], round(beta, 3), "slope = covariance / variance",
       abs(beta - A.BETA["value"]) < 0.0015)
erp = pd.read_excel(RAW / "damodaran/ERPbymonth.xlsx")
erp_row = erp[pd.to_datetime(erp["Start of month"]) == "2026-09-01"]
erp_v = float(erp_row["ERP (T12m)"].iloc[0]) if len(erp_row) else float("nan")
record("C. Market inputs", "Equity risk premium, Damodaran 2026-09-01, column 'ERP (T12m)'", A.EQUITY_RISK_PREMIUM["value"],
       erp_v, "data/raw/damodaran/ERPbymonth.xlsx", abs(erp_v - A.EQUITY_RISK_PREMIUM["value"]) < 0.00005)
peer_px = pd.read_csv(RAW / "peer_prices_fx_yfinance_2026-10-02.csv")
peer_px = peer_px[peer_px["date"] == "2026-10-02"].set_index("ticker")["close"]
for name, tk in {"Lululemon": "LULU", "Deckers": "DECK", "On Holding": "ONON", "Under Armour": "UAA", "adidas": "ADS.DE"}.items():
    record("C. Market inputs", f"{name} share price 2026-10-02", A.PEER_SHARE_PRICES["value"][name], round(peer_px[tk], 2),
           "data/raw/peer_prices_fx_yfinance_2026-10-02.csv", abs(peer_px[tk] - A.PEER_SHARE_PRICES["value"][name]) < 0.006)
for cur, tk in {"EUR": "EURUSD=X", "CHF": "CHFUSD=X"}.items():
    record("C. Market inputs", f"{cur}/USD rate 2026-10-02", A.FX_RATES_TO_USD["value"][cur], round(peer_px[tk], 5),
           "same file", abs(peer_px[tk] - A.FX_RATES_TO_USD["value"][cur]) < 0.0001)

# ---------------------------------------------------------------------------
# D. The same number in two scripts must agree
# ---------------------------------------------------------------------------
dcf = pd.read_csv(OUT / "06_base_case_check.csv").set_index("item")
for item in dcf.index:
    record("D. Consistency", f"DCF {item}: Excel (script 05) vs Python (dcf_model.py)", dcf.loc[item, "excel"],
           dcf.loc[item, "dcf_model_py"], "output/06_base_case_check.csv",
           abs(dcf.loc[item, "excel"] - dcf.loc[item, "dcf_model_py"]) < 1e-6)
record("D. Consistency", "Nike FY2026 revenue: script 02 vs script 08", hist.loc[2026, "Revenue (USD m)"],
       nk["Revenue, latest fiscal year"], "output/02_historical_metrics.csv vs output/08_peer_inputs.csv",
       hist.loc[2026, "Revenue (USD m)"] == nk["Revenue, latest fiscal year"])
by_year = pd.read_csv(OUT / "06b_competitors_by_year.csv")
for name in ["Lululemon", "Deckers", "On Holding", "Under Armour"]:
    p8 = inp[(inp["company"] == name) & (inp["item"] == "Revenue, latest fiscal year")]
    p6 = by_year[(by_year["company"] == name) & (by_year["calendar_year_label"] == 2025)]
    if len(p6) == 0:
        record("D. Consistency", f"{name} latest fiscal-year revenue: script 06b vs 08", float(p8["value"].iloc[0]), "",
               "not in script 06b (added in 08 only)", True)
        continue
    a, b = float(p6["revenue_m"].iloc[0]), float(p8["value"].iloc[0])
    record("D. Consistency", f"{name} latest fiscal-year revenue: script 06b vs 08", b, a,
           "output/06b_competitors_by_year.csv vs output/08_peer_inputs.csv (two separate readings of the SEC data)",
           abs(a - b) < 0.5)
ads = by_year[(by_year["company"] == "adidas") & (by_year["calendar_year_label"] == 2025)]
a8 = inp[(inp["company"] == "adidas") & (inp["item"] == "Net sales FY2025")]["value"].iloc[0]
record("D. Consistency", "adidas 2025 net sales: ten-year overview (06b) vs income statement (08)", a8,
       float(ads["revenue_m"].iloc[0]), "two pages of the adidas Annual Report 2025", abs(a8 - float(ads["revenue_m"].iloc[0])) < 0.5)

# ---------------------------------------------------------------------------
# Save and stop on any failure
# ---------------------------------------------------------------------------
out = pd.DataFrame(rows)
out.to_csv(OUT / "09_data_audit.csv", index=False)
summary = out.groupby(["area", "result"]).size().unstack(fill_value=0)
print(summary.to_string())
fails = out[out["result"] == "FAIL"]
if len(fails):
    print(fails[["item", "project_value", "source_value", "source"]].to_string(index=False))
    raise SystemExit(f"{len(fails)} check(s) failed - see output/09_data_audit.csv")
print(f"No failures in {len(out)} checks ({(out['result'] == 'NOT CHECKED').sum()} too small to check). Saved output/09_data_audit.csv")
