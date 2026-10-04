"""
dcf_model.py  -  The project's ONE discounted-cash-flow model, written out in Python

WHAT THIS IS, IN PLAIN LANGUAGE
-------------------------------
Scripts 04 (reverse DCF), 05 (Excel model) and 06 (implied growth and margin)
used to each carry their own version of the DCF, and they disagreed: different
forecast lengths, different ways of charging for reinvestment, and different
terminal values. This file is the single version they now share. Script 05 builds
the same formulas in Excel, and script 06 checks that the Excel answer and this
file's answer are identical to the cent.

It is not a script you run; other scripts import it:
    import dcf_model as D
    D.value_per_share([0.01, 0.03, 0.04, 0.04, 0.04], target_margin=0.125)

THE MODEL, LINE BY LINE (all money in USD millions, nominal)
-----------------------------------------------------------
Forecast years FY2027-FY2031 (5 years, assumptions.EXCEL_FORECAST_YEARS):
  revenue_t     = revenue_(t-1) x (1 + growth_t)
  FY2027 (t=1) is set from Nike's own guidance (8-K, 2026-10-01): revenue growth
  -8% and an adjusted operating margin of about 5.6% (assumptions.FY2027_OPERATING_MARGIN).
  Every run keeps FY2027 there, including the reverse DCFs, which solve for FY2028-31.
  margin_t      = FY2027 margin + (target - FY2027 margin) x min(t - 1, 4) / 4
                  (straight line from the FY2027 guidance margin to the target in FY2031)
  NOPAT_t       = revenue_t x margin_t x (1 - 18% tax)
  D&A_t         = 1.7% x revenue_t           capex_t = 2.0% x revenue_t
  working cap_t = 11.5% x revenue_t           (FY2026 actual from output/02_historical_metrics.csv)
  FCFF_t        = NOPAT_t + D&A_t - capex_t - (working cap_t - working cap_(t-1))
  PV_t          = FCFF_t x share counted (75% for FY2027) / (1 + WACC)^(years from valuation date to May 31)

Terminal value (value at the end of FY2031 of every year after it):
  FY2032 is built as a normal year in which revenue grows at the terminal rate (2.5%):
  revenue_2032  = revenue_2031 x 1.025
  FCFF_2032     = revenue_2032 x (FY2031 margin x (1 - tax) + D&A% - capex%)
                  - 11.5% x (revenue_2032 - revenue_2031)
  terminal      = FCFF_2032 / (WACC - 2.5%), discounted like FY2031.
  (Why not just FY2031 FCFF x 1.025? FY2031's cash flow includes the working
  capital needed for FY2031's own growth rate. Growing it forever would charge,
  say, 8%-growth investment forever while revenue only grows 2.5%, or count cash
  released by shrinking as if it kept coming forever.)

Equity value per share = (sum of PVs + PV of terminal + cash + short-term
investments - debt excl. leases) / diluted shares.

The discount rate (WACC) is built in wacc_table() from assumptions.py and the
latest balance sheet (output/04_latest_balance_sheet_and_shares.csv, written by
script 04 from the Q1 FY2027 10-Q).
"""

from datetime import date
from pathlib import Path

import pandas as pd

import assumptions as A

ROOT = Path(__file__).resolve().parent.parent
METRICS_CSV = ROOT / "output/02_historical_metrics.csv"
BALANCE_SHEET_CSV = ROOT / "output/04_latest_balance_sheet_and_shares.csv"
FY = "Fiscal year (ends May 31)"


def v(name):
    """One assumption's value from assumptions.py."""
    return getattr(A, name)["value"]


BASE_FY = v("BASE_FISCAL_YEAR")                                          # 2026
FC_YEARS = list(range(BASE_FY + 1, BASE_FY + 1 + v("EXCEL_FORECAST_YEARS")))   # 2027..2031
VALUATION_DATE = date.fromisoformat(v("VALUATION_DATE"))


def base_year():
    """FY2026 actuals the forecast starts from (SEC 10-K, via script 02)."""
    h = pd.read_csv(METRICS_CSV).set_index(FY)
    return {
        "revenue": h.loc[BASE_FY, "Revenue (USD m)"],
        # recomputed from the two USD lines (the % column in the CSV is rounded to 2 decimals)
        "margin": h.loc[BASE_FY, "Operating income = gross profit - S&A (USD m)"] / h.loc[BASE_FY, "Revenue (USD m)"],
        "working_capital": h.loc[BASE_FY, "Operating working capital = AR + inventories + prepaid - AP - accrued (USD m)"],
    }


def balance_sheet():
    """Cash, debt and shares from the latest 10-Q (written by script 04)."""
    b = pd.read_csv(BALANCE_SHEET_CSV).set_index("item")["value"]
    return {
        "cash_and_st_investments": b["Cash + short-term investments (USD m)"],
        "debt": b["Total debt, excl. leases (USD m)"],
        "shares": b["Diluted weighted-average shares, latest quarter (millions)"],
    }


def wacc_table():
    """Discount rate, step by step: list of (item, value) rows. The last row is the WACC."""
    bs = balance_sheet()
    price = v("SHARE_PRICE")
    market_cap = price * bs["shares"]
    cost_equity = v("RISK_FREE_RATE") + v("BETA") * v("EQUITY_RISK_PREMIUM")          # CAPM
    pretax_debt = v("RISK_FREE_RATE") + v("PRETAX_COST_OF_DEBT_SPREAD")
    aftertax_debt = pretax_debt * (1 - v("TAX_RATE_ON_INTEREST"))
    w_e = market_cap / (market_cap + bs["debt"])
    w_d = bs["debt"] / (market_cap + bs["debt"])
    return [
        ("Share price (USD)", price),
        ("Shares, diluted (millions)", bs["shares"]),
        ("Market value of equity = price x shares (USD m)", market_cap),
        ("Debt, book value excl. leases (USD m)", bs["debt"]),
        ("Risk-free rate (%)", v("RISK_FREE_RATE") * 100),
        ("Beta", v("BETA")),
        ("Equity risk premium (%)", v("EQUITY_RISK_PREMIUM") * 100),
        ("Cost of equity = risk-free + beta x ERP (%)", cost_equity * 100),
        ("Pre-tax cost of debt = risk-free + spread (%)", pretax_debt * 100),
        ("After-tax cost of debt = pre-tax x (1 - tax rate) (%)", aftertax_debt * 100),
        ("Weight of equity = equity / (equity + debt) (%)", w_e * 100),
        ("Weight of debt = debt / (equity + debt) (%)", w_d * 100),
        ("WACC = w_equity x cost of equity + w_debt x after-tax cost of debt (%)",
         (w_e * cost_equity + w_d * aftertax_debt) * 100),
    ]


WACC = wacc_table()[-1][1] / 100


def base_case_growth():
    """The Excel model's base-case growth path FY2027-FY2031. The scenario adjustment (0 by default)
    is added to FY2028-31 only: FY2027 stays at Nike's guidance."""
    return [v("EXCEL_REVENUE_GROWTH")[y] + (v("EXCEL_GROWTH_ADJUSTMENT") if y > FC_YEARS[0] else 0.0)
            for y in FC_YEARS]


def constant(g):
    """FY2027 at Nike's guidance, then the same growth rate g in every year FY2028-FY2031."""
    return [v("EXCEL_REVENUE_GROWTH")[FC_YEARS[0]]] + [g] * (len(FC_YEARS) - 1)


def fy2027_margin():
    """FY2027 operating margin, from Nike's guidance (assumptions.py; script 10 shows the steps)."""
    return v("FY2027_OPERATING_MARGIN")


def margin_for_year(t, target_margin, years_to_target):
    """Operating margin in forecast year t (1 = FY2027): the guidance margin in FY2027, then a
    straight line to the target, reached years_to_target years after FY2026 (5 = FY2031)."""
    m27 = fy2027_margin()
    if t == 1:
        return m27
    return m27 + (target_margin - m27) * min(t - 1, years_to_target - 1) / (years_to_target - 1)


def run(growth_by_year, target_margin=None, years_to_target=None, wacc=None, terminal_growth=None):
    """Full model. Returns (value per share, year-by-year table, summary dict)."""
    target_margin = v("TARGET_OPERATING_MARGIN") if target_margin is None else target_margin
    ytt = years_to_target or v("YEARS_TO_REACH_TARGET_MARGIN")
    wacc = WACC if wacc is None else wacc
    g_term = v("TERMINAL_GROWTH") if terminal_growth is None else terminal_growth
    tax, da_pct, capex_pct, nwc_pct = v("FORECAST_TAX_RATE"), v("DA_PCT_OF_REVENUE"), v("CAPEX_PCT_OF_REVENUE"), v("NWC_PCT_OF_REVENUE")
    base, bs = base_year(), balance_sheet()

    rows, rev_prev, nwc_prev = [], base["revenue"], base["working_capital"]
    for t, (fy, g) in enumerate(zip(FC_YEARS, growth_by_year), start=1):
        revenue = rev_prev * (1 + g)
        margin = margin_for_year(t, target_margin, ytt)
        op_income = revenue * margin
        nopat = op_income * (1 - tax)
        da, capex, nwc = revenue * da_pct, revenue * capex_pct, revenue * nwc_pct
        fcff = nopat + da - capex - (nwc - nwc_prev)
        years = (date(fy, 5, 31) - VALUATION_DATE).days / 365.25
        share = v("SHARE_OF_FY2027_REMAINING") if t == 1 else 1.0
        disc = 1 / (1 + wacc) ** years
        rows.append({FY: fy, "Revenue growth": g, "Revenue (USD m)": revenue, "Operating margin": margin,
                     "Operating income (USD m)": op_income, "NOPAT (USD m)": nopat, "D&A (USD m)": da,
                     "Capex (USD m)": capex, "Operating working capital (USD m)": nwc,
                     "Increase in working capital (USD m)": nwc - nwc_prev, "FCFF (USD m)": fcff,
                     "Years from valuation date": years, "Share of year counted": share,
                     "Discount factor": disc, "PV of FCFF (USD m)": fcff * share * disc})
        rev_prev, nwc_prev = revenue, nwc
    table = pd.DataFrame(rows)

    last = rows[-1]
    rev_next = last["Revenue (USD m)"] * (1 + g_term)
    fcff_next = (rev_next * (last["Operating margin"] * (1 - tax) + da_pct - capex_pct)
                 - nwc_pct * (rev_next - last["Revenue (USD m)"]))
    terminal = fcff_next / (wacc - g_term)
    pv_terminal = terminal * last["Discount factor"]
    pv_explicit = table["PV of FCFF (USD m)"].sum()
    ev = pv_explicit + pv_terminal
    equity = ev + bs["cash_and_st_investments"] - bs["debt"]
    per_share = equity / bs["shares"]
    summary = {
        "WACC": wacc, "Terminal growth": g_term, "Target operating margin": target_margin,
        f"Sum of PV of FCFF FY{FC_YEARS[0]}-FY{FC_YEARS[-1]} (USD m)": pv_explicit,
        f"FY{FC_YEARS[-1] + 1} revenue = FY{FC_YEARS[-1]} x (1 + terminal growth) (USD m)": rev_next,
        f"FY{FC_YEARS[-1] + 1} FCFF, built as a steady-growth year (USD m)": fcff_next,
        f"Terminal value at end of FY{FC_YEARS[-1]} (USD m)": terminal,
        "PV of terminal value (USD m)": pv_terminal,
        "Terminal value share of enterprise value": pv_terminal / ev,
        "Enterprise value (USD m)": ev,
        "Plus cash + short-term investments (USD m)": bs["cash_and_st_investments"],
        "Minus debt excl. leases (USD m)": bs["debt"],
        "Equity value (USD m)": equity,
        "Diluted shares (millions)": bs["shares"],
        "Value per share (USD)": per_share,
        "Share price (USD)": v("SHARE_PRICE"),
    }
    return per_share, table, summary


def value_per_share(growth_by_year, target_margin=None, **kw):
    return run(growth_by_year, target_margin, **kw)[0]


def bisect(f, lo, hi, tol=None):
    """Find x between lo and hi where f(x) = 0, given f(lo) < 0 < f(hi).

    Try the midpoint; if f is above zero there, the answer is in the lower half,
    otherwise the upper half. Keep halving until |f| < tol. Returns (x, rounds),
    or (nan, 0) if the answer is not inside [lo, hi]."""
    tol = v("SOLVER_TOLERANCE_USD") if tol is None else tol
    if not (f(lo) < 0 < f(hi)):
        return float("nan"), 0
    for rounds in range(1, 200):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if abs(f_mid) < tol:
            return mid, rounds
        if f_mid > 0:
            hi = mid
        else:
            lo = mid
    return mid, rounds


def implied_growth(target_margin=None, years_to_target=None, wacc=None):
    """The one constant growth rate (FY2028-31, after the FY2027 guidance year) that makes value per share = share price."""
    lo, hi = v("IMPLIED_GROWTH_SEARCH_RANGE")
    price = v("SHARE_PRICE")
    return bisect(lambda g: value_per_share(constant(g), target_margin, years_to_target=years_to_target,
                                            wacc=wacc) - price, lo, hi)
