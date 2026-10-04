"""
07_valuation_risk_checks.py  -  Which open questions could lower Nike's base-case valuation, and by how much?

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
The base-case DCF (scripts/dcf_model.py) rests on some inputs we
could not fully pin down. This script changes ONE of them at a time, re-runs the
same model, and records the new value per share and the change from the base case. It
also re-solves the market-implied operating margin at the base-case growth path,
which shows how the reverse-DCF finding moves. At the end it applies every
value-lowering change at once.

The alternative values all live in scripts/assumptions.py under "DOWNSIDE CHECKS",
with their sources. Nothing here changes the base case.

The checks
  1. Equity risk premium: Damodaran's start-of-2026 figure (4.23%) and a higher 5.0%
     (the base uses his latest, 4.09% for 1 Sept 2026).
  2. Risk-free rate: the 4.76% yield of 31 Aug 2026, before September's jump to 5.28%.
  3. Tax rate: 21% instead of 18% (Nike's FY2026 effective rate was 20.3%).
  4. Working capital stays at FY2026's 12.7% of revenue instead of returning to 11.5%.
  5. Terminal growth 2.0% instead of 2.5%.
  6. Leases counted as debt. Nike's USD 3.2bn of operating lease liabilities (10-Q,
     2026-08-31) are added to debt. To stay consistent, the interest part of the lease
     cost, which today sits inside S&A, is taken out of operating cost: operating
     margin rises by (lease liability x Nike's 3.6% weighted-average lease discount
     rate, from the FY2026 10-K) / FY2026 revenue. The WACC is rebuilt with the larger debt.
  Share count: the 10-Q's diluted weighted average (1,484.2m) already includes
  dilution from share awards; the SEC data has no period-end count to compare
  (see the project's XBRL notes), so it is not tested here.

Outputs
  output/07_valuation_risk_checks.csv   one row per check: inputs changed, value per share, change, implied margin
"""

import json
import sys
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assumptions as A
import dcf_model as D

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "data/raw/companyfacts_CIK0000320187_2026-10-04.json"
OUT = ROOT / "output/07_valuation_risk_checks.csv"
PRICE = A.SHARE_PRICE["value"]


# ---------------------------------------------------------------------------
# STEP 1. A way to change assumptions temporarily, then put them back
# ---------------------------------------------------------------------------
@contextmanager
def scenario(values=None, extra_debt=0.0, margin_uplift=0.0):
    """Inside a `with scenario(...)` block the model uses the changed inputs:
    values        {assumption name: new value}
    extra_debt    USD m added to debt (and to the WACC's debt weight)
    margin_uplift added to FY2027's guidance margin and to the target margin (operating cost taken out)"""
    values = dict(values or {})
    if margin_uplift:
        values["FY2027_OPERATING_MARGIN"] = A.FY2027_OPERATING_MARGIN["value"] + margin_uplift
    saved = {k: getattr(A, k) for k in values}
    saved_bs, saved_base = D.balance_sheet, D.base_year
    for k, val in values.items():
        setattr(A, k, {**getattr(A, k), "value": val})
    if extra_debt:
        D.balance_sheet = lambda: {**saved_bs(), "debt": saved_bs()["debt"] + extra_debt}
    D.WACC = D.wacc_table()[-1][1] / 100
    try:
        yield
    finally:
        for k, a in saved.items():
            setattr(A, k, a)
        D.balance_sheet, D.base_year = saved_bs, saved_base
        D.WACC = D.wacc_table()[-1][1] / 100


def measure(name, what, values=None, extra_debt=0.0, margin_uplift=0.0):
    with scenario(values, extra_debt, margin_uplift):
        target = A.TARGET_OPERATING_MARGIN["value"] + margin_uplift
        value = D.value_per_share(D.base_case_growth(), target)
        # market-implied FY2031 margin at the base-case growth path: bisection on the margin
        m, _ = D.bisect(lambda m: D.value_per_share(D.base_case_growth(), m) - PRICE, -0.10, 0.40)
        return {"check": name, "what_changes": what, "wacc_pct": D.WACC * 100,
                "value_per_share_usd": value,
                "implied_fy2031_margin_at_base_growth_pct": (m - margin_uplift) * 100}


# ---------------------------------------------------------------------------
# STEP 2. Lease liabilities from the latest 10-Q (SEC XBRL)
# ---------------------------------------------------------------------------
facts = json.loads(FACTS.read_text())["facts"]["us-gaap"]
bs_date = pd.read_csv(ROOT / "output/04_latest_balance_sheet_and_shares.csv").dropna(subset=["period_end"])["period_end"].iloc[0]


def at_date(tag):
    rows = [x for x in facts[tag]["units"]["USD"] if x["end"] == bs_date]
    best = max(rows, key=lambda x: x["filed"])
    return best["val"] / 1e6, best["accn"]


lease_cur, accn = at_date("OperatingLeaseLiabilityCurrent")
lease_non, _ = at_date("OperatingLeaseLiabilityNoncurrent")
leases = lease_cur + lease_non
# Interest part of the lease cost: liability x Nike's own weighted-average lease discount rate
# (10-K FY2026, XBRL OperatingLeaseWeightedAverageDiscountRatePercent).
rate_rows = [x for x in facts["OperatingLeaseWeightedAverageDiscountRatePercent"]["units"]["pure"]]
lease_rate = max(rate_rows, key=lambda x: (x["end"], x["filed"]))["val"]
lease_interest = leases * lease_rate
margin_uplift = lease_interest / D.base_year()["revenue"]

# ---------------------------------------------------------------------------
# STEP 3. Run every check
# ---------------------------------------------------------------------------
erp_jan, erp_high = A.CHECK_EQUITY_RISK_PREMIUM_START_2026["value"], A.CHECK_EQUITY_RISK_PREMIUM_HIGH["value"]
erp_base = A.EQUITY_RISK_PREMIUM["value"]
rf_aug, tax_hi = A.CHECK_RISK_FREE_AUG_31["value"], A.CHECK_TAX_RATE_HIGH["value"]
nwc_hi, g_lo = A.CHECK_NWC_STAYS_AT_FY2026["value"], A.CHECK_TERMINAL_GROWTH_LOW["value"]

rows = [measure("Base case", "nothing")]
rows.append(measure("ERP start of 2026", f"equity risk premium {erp_base:.2%} -> {erp_jan:.2%} (Damodaran 2026-01-01)", {"EQUITY_RISK_PREMIUM": erp_jan}))
rows.append(measure("ERP high", f"equity risk premium {erp_base:.2%} -> {erp_high:.2%}", {"EQUITY_RISK_PREMIUM": erp_high}))
rows.append(measure("Risk-free 31 Aug", f"risk-free 5.28% -> {rf_aug:.2%}", {"RISK_FREE_RATE": rf_aug}))
rows.append(measure("Tax 21%", f"tax on operating income 18% -> {tax_hi:.0%}", {"FORECAST_TAX_RATE": tax_hi}))
rows.append(measure("Working capital stays high", f"working capital 11.5% -> {nwc_hi:.1%} of revenue",
                    {"NWC_PCT_OF_REVENUE": nwc_hi}))
rows.append(measure("Terminal growth 2%", f"terminal growth 2.5% -> {g_lo:.1%}", {"TERMINAL_GROWTH": g_lo}))
rows.append(measure("Leases as debt",
                    f"+USD {leases:,.0f}m lease debt (10-Q accn {accn}); margin +{margin_uplift:.2%} "
                    f"(lease interest {lease_interest:,.0f}m at {lease_rate:.2%})",
                    extra_debt=leases, margin_uplift=margin_uplift))

base_value = rows[0]["value_per_share_usd"]
lowering = [r["check"] for r in rows[1:] if r["value_per_share_usd"] < base_value]
combined = {}
lease_in = "Leases as debt" in lowering
for r_name, (k, val) in {"ERP high": ("EQUITY_RISK_PREMIUM", erp_high), "Tax 21%": ("FORECAST_TAX_RATE", tax_hi),
                         "Working capital stays high": ("NWC_PCT_OF_REVENUE", nwc_hi),
                         "Terminal growth 2%": ("TERMINAL_GROWTH", g_lo)}.items():
    if r_name in lowering:
        combined[k] = val
rows.append(measure("All value-lowering checks together", ", ".join(lowering), combined,
                    extra_debt=leases if lease_in else 0.0, margin_uplift=margin_uplift if lease_in else 0.0))

out = pd.DataFrame(rows)
out["change_vs_base_usd"] = out["value_per_share_usd"] - base_value
out["value_vs_price_pct"] = (out["value_per_share_usd"] / PRICE - 1) * 100
out.round(3).to_csv(OUT, index=False)
print(out[["check", "wacc_pct", "value_per_share_usd", "change_vs_base_usd", "value_vs_price_pct",
           "implied_fy2031_margin_at_base_growth_pct"]].round(2).to_string(index=False))
print(f"\nLeases: {leases:,.0f}m at {bs_date}; saved {OUT.relative_to(ROOT)}")
