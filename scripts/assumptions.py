"""
assumptions.py  -  The ONE place where modeling assumptions and metric definitions live

WHAT THIS IS, IN PLAIN LANGUAGE
-------------------------------
Every choice that could change a result (a tax rate, a definition, a timing
convention) is written down here, once, with:
    value     - the number or setting itself
    unit      - what the value is measured in
    source    - where it came from, or "judgment" if it is our own call
    date_set  - when we decided it
Other scripts import these values; none of them may type in a modeling number of
their own (project rule 3). To change an assumption, change it here and re-run.
"""

# ---------------------------------------------------------------------------
# HISTORICAL METRIC DEFINITIONS (used by 02_historical_metrics.py)
# ---------------------------------------------------------------------------
# These are definitions rather than forecasts, but they are still choices, so
# they are recorded here.

FCF_DEFINITION = {
    "value": "Free cash flow = operating cash flow - capital expenditures",
    "unit": "USD millions",
    "source": "judgment (the most common simple definition; both inputs are SEC 10-K cash flow statement lines)",
    "date_set": "2026-10-04",
}

ROIC_DEFINITION = {
    "value": (
        "ROIC = operating income x (1 - tax rate) / invested capital, where "
        "invested capital = total debt (excl. leases) + shareholders' equity "
        "- cash and equivalents - short-term investments"
    ),
    "unit": "% (fraction)",
    "source": "judgment (standard 'financing side' invested capital; leases left out to match the project's total-debt definition)",
    "date_set": "2026-10-04",
}

# Which balance sheet date to use for invested capital.
# "year_end" = the balance at the end of the same fiscal year (May 31).
# (The alternative, an average of the start and end of the year, smooths out
# swings but needs one extra year of data. Year-end is simpler to check by hand.)
ROIC_INVESTED_CAPITAL_TIMING = {
    "value": "year_end",
    "unit": "setting",
    "source": "judgment",
    "date_set": "2026-10-04",
}

# Tax rate used in ROIC.
# Main ROIC column: each year's ACTUAL effective tax rate
#   = income tax expense / income before income taxes (both from the 10-K).
# Second ROIC column: one NORMALIZED rate for every year, because the actual rate
# jumps around for one-off reasons. FY2018 is the big one: the US Tax Cuts and
# Jobs Act forced a one-time charge, so Nike's FY2018 rate was 55.3%.
# 15% is roughly the median of Nike's actual rates FY2017-FY2026 excluding
# FY2018 (median of the other nine years = 14.9%).
ROIC_TAX_RATE_METHOD = {
    "value": "actual_effective_rate_each_year",
    "unit": "setting",
    "source": "judgment",
    "date_set": "2026-10-04",
}

NORMALIZED_TAX_RATE = {
    "value": 0.15,
    "unit": "fraction (15%)",
    "source": "judgment: ~median of Nike's FY2017-FY2026 effective tax rates excl. FY2018 (14.9%), per SEC 10-K data",
    "date_set": "2026-10-04",
}

# Treat a missing short-term borrowings value as zero (FY2026 has no tagged value;
# 01_download.py already does this when it builds total debt).
MISSING_SHORT_TERM_BORROWINGS_AS_ZERO = {
    "value": True,
    "unit": "setting",
    "source": "judgment (Nike's notes payable is tiny, USD 5-10m in recent years)",
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# MARKET DATA SETTINGS (used by 03_market_inputs.py)
# ---------------------------------------------------------------------------
VALUATION_DATE = {
    "value": "2026-10-02",
    "unit": "date",
    "source": "judgment: last trading day before this model was built (2026-10-04 was a Sunday)",
    "date_set": "2026-10-04",
}

BETA_LOOKBACK_MONTHS = {
    "value": 60,
    "unit": "months",
    "source": "judgment: common convention (5 years of monthly returns)",
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# MARKET INPUTS (non-SEC; used by 04_reverse_dcf.py)
# Values copied from the output of 03_market_inputs.py unless noted.
# ---------------------------------------------------------------------------
SHARE_PRICE = {
    "value": 33.87,
    "unit": "USD per share",
    "source": "Yahoo Finance NKE close on 2026-10-02 (03_market_inputs.py); NON-SEC",
    "date_set": "2026-10-04",
}

RISK_FREE_RATE = {
    "value": 0.05277,
    "unit": "fraction per year (5.277%)",
    "source": "10-year US Treasury yield, Yahoo ^TNX close on 2026-10-02 (03_market_inputs.py); NON-SEC",
    "date_set": "2026-10-04",
}

EQUITY_RISK_PREMIUM = {
    "value": 0.0409,
    "unit": "fraction per year (4.09%)",
    "source": ("Damodaran implied US equity risk premium on 2026-09-01, 'ERP (T12m)' series, his latest monthly figure "
               "before the 2026-10-02 valuation date. Verified in his ERPbymonth.xlsx, saved in data/raw/damodaran/ "
               "(downloaded 2026-10-04). Changed from 4.23% (his 2026-01-01 figure) on 2026-10-04 so the premium is "
               "as current as the share price and risk-free rate. NON-SEC"),
    "date_set": "2026-10-04",
}

BETA = {
    "value": 1.092,
    "unit": "multiple of market moves",
    "source": "regression of 60 monthly Nike returns on S&P 500 returns, Oct-2021 to Sep-2026 (03_market_inputs.py, output/03_beta_summary.csv)",
    "date_set": "2026-10-04",
}

PRETAX_COST_OF_DEBT_SPREAD = {
    "value": 0.008,
    "unit": "fraction per year over the risk-free rate (0.8%)",
    "source": "judgment: typical spread for a high-grade (A/AA) US corporate borrower like Nike",
    "date_set": "2026-10-04",
}

TAX_RATE_ON_INTEREST = {
    "value": 0.21,
    "unit": "fraction",
    "source": "US federal statutory corporate tax rate (interest is deducted mostly in the US)",
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# DCF STRUCTURE (used by dcf_model.py, the one DCF shared by scripts 04, 05 and 06)
# On 2026-10-04 the separate 10-year / sales-to-capital version used by script 04
# (FORECAST_YEARS = 10, SALES_TO_CAPITAL = 3.2) was retired so all scripts agree.
# ---------------------------------------------------------------------------
BASE_FISCAL_YEAR = {
    "value": 2026,
    "unit": "fiscal year",
    "source": "latest full fiscal year in the 10-K (FY2026 ended 2026-05-31)",
    "date_set": "2026-10-04",
}


TARGET_OPERATING_MARGIN = {
    "value": 0.125,
    "unit": "fraction of revenue (12.5%)",
    "source": "judgment: Nike's FY2017-FY2024 operating margin, simple average of the 8 years = 12.5% (output/02_historical_metrics.csv), i.e. a full recovery to pre-FY2025 levels",
    "date_set": "2026-10-04",
}

YEARS_TO_REACH_TARGET_MARGIN = {
    "value": 5,
    "unit": "years after FY2026 (FY2027 is the guidance margin; from there a straight line to target by FY2031)",
    "source": "judgment",
    "date_set": "2026-10-04",
}

FY2027_OPERATING_MARGIN = {
    "value": 0.0555,
    "unit": "fraction of revenue (adjusted: before Pace restructuring charges)",
    "source": ("derived from Nike's FY2027 guidance (GUIDANCE_FY2027, midpoints): adjusted EPS 1.25 x 1,484.2m diluted shares "
               "/ (1 - 25% tax) - 103m non-operating income = USD 2,371m operating income, / (46,398m x (1 - 8%)) revenue "
               "= 5.55%. Script 10 repeats the steps and checks this value (output/10_guidance_margin.csv). Set 2026-10-04 "
               "at Eric's request to build the guidance into the base case; before that FY2027 sat on the straight line "
               "from FY2026's 8.2% (9.1%)"),
    "date_set": "2026-10-04",
}

FORECAST_TAX_RATE = {
    "value": 0.18,
    "unit": "fraction of operating income",
    "source": "judgment: about Nike's FY2023-FY2026 average effective rate (17.6%, output/02_historical_metrics.csv)",
    "date_set": "2026-10-04",
}


TERMINAL_GROWTH = {
    "value": 0.025,
    "unit": "fraction per year, forever after FY2031",
    "source": "judgment: roughly long-run inflation plus a little real growth; kept below the risk-free rate",
    "date_set": "2026-10-04",
}

SHARE_OF_FY2027_REMAINING = {
    "value": 0.75,
    "unit": "fraction of FY2027 cash flow still to come",
    "source": "Q1 FY2027 (Jun-Aug 2026) is already over and its cash is in the 2026-08-31 balance sheet, so only 9 of 12 months count",
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# FORECAST DRIVERS (dcf_model.py; the Excel model 05 shows the same formulas)
# Used by the forward DCF (base-case growth path below) and the reverse DCFs
# (scripts 04 and 06, which replace the growth path with the unknown rate).
# ---------------------------------------------------------------------------
EXCEL_FORECAST_YEARS = {
    "value": 5,
    "unit": "years (FY2027-FY2031); used by every DCF in the project",
    "source": "Eric's request (5-year forecast); margin reaches its target in year 5, and FY2032 is built as a steady 2.5%-growth year for the terminal value",
    "date_set": "2026-10-04",
}

EXCEL_REVENUE_GROWTH = {
    "value": {2027: -0.08, 2028: 0.03, 2029: 0.04, 2030: 0.04, 2031: 0.04},
    "unit": "fraction per year, by fiscal year",
    "source": ("FY2027 = midpoint of Nike's guidance, revenue to 'decline high-single digits' (read as -7% to -9%; "
               "Q1 FY2027 earnings release, 8-K 0000320187-26-000184, Ex. 99.1, 2026-10-01; see GUIDANCE_FY2027). "
               "History: +1% until 2026-10-04 22:35, then -1.09% (Q1 actual + Q2-Q4 flat) until 2026-10-04 23:00. "
               "FY2028-31: judgment, a gradual return toward, but below, Nike's FY2016-FY2024 compound annual growth of "
               "5.9% (output/06a_nike_history_fy1993_fy2026.csv)"),
    "date_set": "2026-10-04",
}

EXCEL_GROWTH_ADJUSTMENT = {
    "value": 0.0,
    "unit": "fraction per year, added to every forecast year's growth",
    "source": "setting for scenario testing (e.g. Excel Goal Seek to find the growth that matches the share price); 0 = base case",
    "date_set": "2026-10-04",
}

DA_PCT_OF_REVENUE = {
    "value": 0.017,
    "unit": "fraction of revenue",
    "source": "Nike FY2017-FY2026 average depreciation & amortization / revenue = 1.72% (10-K cash flow statements)",
    "date_set": "2026-10-04",
}

CAPEX_PCT_OF_REVENUE = {
    "value": 0.02,
    "unit": "fraction of revenue",
    "source": ("judgment: Nike FY2017-FY2026 average capex / revenue = 2.09%; FY2025-26 (0.9%, 1.5%) look cut back "
               "during the downturn, so we assume a return toward the average, a bit above D&A so the asset base grows"),
    "date_set": "2026-10-04",
}

NWC_PCT_OF_REVENUE = {
    "value": 0.115,
    "unit": "fraction of revenue",
    "source": ("Nike FY2017-FY2026 average operating working capital / revenue = 11.4% (10-K balance sheets). "
               "Operating working capital = receivables + inventories + prepaid & other current assets "
               "- accounts payable - accrued liabilities. FY2026 was 12.7%, so FY2027 releases some cash"),
    "date_set": "2026-10-04",
}

SENSITIVITY_WACC_STEP = {
    "value": 0.005,
    "unit": "fraction (0.5 percentage points between columns of the sensitivity table)",
    "source": "judgment (presentation only)",
    "date_set": "2026-10-04",
}

SENSITIVITY_GROWTH_STEP = {
    "value": 0.005,
    "unit": "fraction (0.5 percentage points between rows of the sensitivity table)",
    "source": "judgment (presentation only)",
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# MARKET-IMPLIED GROWTH AND MARGIN (used by 06_implied_growth_and_margin.py)
# The solver reuses every input of the 5-year Excel model (read from
# output/05_nike_dcf_model.xlsx). Only the two unknowns change: one revenue
# growth rate used in every year FY2028-FY2031 (FY2027 is Nike's guidance), and the operating margin
# reached by FY2031. These settings say where to look and how to show it.
# ---------------------------------------------------------------------------
IMPLIED_MARGIN_GRID = {
    "value": [0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.125, 0.13, 0.14, 0.15, 0.16],
    "unit": "fraction of revenue (operating margin reached by FY2031)",
    "source": "judgment: covers Nike's FY1993-FY2026 range (8.0% FY2025 low to 15.8% FY1993/FY2021 highs, output/06a_nike_history_fy1993_fy2026.csv)",
    "date_set": "2026-10-04",
}

IMPLIED_GROWTH_SEARCH_RANGE = {
    "value": (-0.20, 0.40),
    "unit": "fraction per year (lowest and highest growth the solver will try)",
    "source": "judgment: wide enough that every margin in the grid has an answer inside it",
    "date_set": "2026-10-04",
}

SOLVER_TOLERANCE_USD = {
    "value": 0.001,
    "unit": "USD per share (stop when model value is within this of the price)",
    "source": "judgment (a tenth of a cent)",
    "date_set": "2026-10-04",
}

HISTORY_REFERENCE_YEARS = {
    "value": (2017, 2024),
    "unit": "fiscal years (first, last) used as 'normal Nike': growth = compound annual rate over those years (from the year before), margin = simple average",
    "source": "judgment: same window as TARGET_OPERATING_MARGIN and EXCEL_REVENUE_GROWTH (the 8 years before the FY2025 slump)",
    "date_set": "2026-10-04",
}

HEATMAP_GROWTH_RANGE = {
    "value": (-0.02, 0.08, 0.01),
    "unit": "fraction per year (first, last, step) for the heatmap rows",
    "source": "judgment (presentation only)",
    "date_set": "2026-10-04",
}

HEATMAP_MARGIN_RANGE = {
    "value": (0.06, 0.16, 0.01),
    "unit": "fraction of revenue (first, last, step) for the heatmap columns",
    "source": "judgment (presentation only)",
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# DOWNSIDE CHECKS (used by 07_valuation_risk_checks.py)
# Alternative values for the open factors that could LOWER the valuation. They
# are tests, not the base case: the base case above is unchanged.
# ---------------------------------------------------------------------------
CHECK_EQUITY_RISK_PREMIUM_START_2026 = {
    "value": 0.0423,
    "unit": "fraction per year (4.23%)",
    "source": "Damodaran implied US ERP on 2026-01-01, same series (data/raw/damodaran/ERPbymonth.xlsx); the project's base value until 2026-10-04. NON-SEC",
    "date_set": "2026-10-04",
}

CHECK_EQUITY_RISK_PREMIUM_HIGH = {
    "value": 0.05,
    "unit": "fraction per year (5.0%)",
    "source": "judgment: a round, commonly used practitioner ERP; above every monthly Damodaran figure of the last 12 months (3.9%-4.8%)",
    "date_set": "2026-10-04",
}

CHECK_RISK_FREE_AUG_31 = {
    "value": 0.04758,
    "unit": "fraction per year (4.758%)",
    "source": "10-year US Treasury yield on 2026-08-31 (^TNX in data/raw/market_data_NKE_GSPC_TNX_yfinance_2026-10-02.csv), before September's jump to 5.28%; NON-SEC",
    "date_set": "2026-10-04",
}

CHECK_TAX_RATE_HIGH = {
    "value": 0.21,
    "unit": "fraction of operating income",
    "source": "US federal statutory rate; Nike's FY2026 effective rate was 20.3% (output/02_historical_metrics.csv), above the 18% base",
    "date_set": "2026-10-04",
}

CHECK_NWC_STAYS_AT_FY2026 = {
    "value": 0.127,
    "unit": "fraction of revenue",
    "source": "Nike's FY2026 operating working capital / revenue = 12.7% (output/02_historical_metrics.csv): no return to the 11.5% average",
    "date_set": "2026-10-04",
}

CHECK_TERMINAL_GROWTH_LOW = {
    "value": 0.02,
    "unit": "fraction per year",
    "source": "judgment: inflation-only long-run growth (no real growth)",
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# PEER MULTIPLES (used by 08_peer_multiples.py)
# Share prices and exchange rates for comparing Nike with five competitors.
# All on the same day as Nike's SHARE_PRICE above (2026-10-02), so every multiple is measured at once.
# Raw Yahoo download saved as data/raw/peer_prices_fx_yfinance_2026-10-02.csv;
# script 08 checks these typed-in values against that file.
# ---------------------------------------------------------------------------
PEER_SHARE_PRICES = {
    "value": {"Lululemon": 94.46, "Deckers": 79.12, "On Holding": 30.85,
              "Under Armour": 4.71, "adidas": 144.05},
    "unit": "price per share in the trading currency: USD, except adidas in EUR (Xetra)",
    "source": ("Yahoo Finance closes on 2026-10-02 for NKE, LULU, DECK, ONON (NYSE, USD), UAA (class A, USD) and "
               "ADS.DE (Xetra, EUR); NON-SEC. Under Armour's class C (UA) closed at 4.59; class A is used for all shares"),
    "date_set": "2026-10-04",
}

FX_RATES_TO_USD = {
    "value": {"USD": 1.0, "EUR": 1.1250, "CHF": 1.2041},
    "unit": "USD per 1 unit of the currency",
    "source": ("Yahoo Finance EURUSD=X (1.12499) and CHFUSD=X (1.20405) closes on 2026-10-02, rounded to 4 decimals; NON-SEC. "
               "Used to show adidas and On sizes in USD, and to put On's CHF figures on the same basis as its USD share price"),
    "date_set": "2026-10-04",
}

PEER_GROWTH_CAGR_YEARS = {
    "value": 3,
    "unit": "fiscal years",
    "source": "judgment: long enough to smooth one odd year, short enough to describe the current business (adidas's Reebok break, 2019/2020, falls outside the window)",
    "date_set": "2026-10-04",
}

PEER_IFRS_LEASE_ADJUSTMENT = {
    "value": True,
    "unit": "on/off",
    "source": ("judgment: adidas and On report under IFRS, where store rents are split into right-of-use depreciation (inside D&A) "
               "and lease interest (below operating profit), so their raw EBITDA excludes rent. US GAAP companies (Nike and the "
               "rest) count rent as an operating cost. Because enterprise value excludes leases for everyone (as in Nike's DCF), "
               "IFRS EBITDA is put on the US basis: EBITDA = operating profit + D&A - right-of-use depreciation - lease interest"),
    "date_set": "2026-10-04",
}

CHECK_ON_FX_AVERAGE_RATE = {
    "value": 1.2608,
    "unit": "USD per CHF",
    "source": ("average of daily Yahoo CHFUSD=X closes, 2025-07-01 to 2026-06-30 (On's last twelve months), saved as "
               "data/raw/CHFUSD_daily_yfinance_2025-07-01_to_2026-06-30.csv; NON-SEC. A check: the base case converts On's "
               "CHF figures at the 2026-10-02 spot rate, the same day as the share price"),
    "date_set": "2026-10-04",
}

# ---------------------------------------------------------------------------
# MEMO SCENARIOS (script 10, the investment memo of 2026-10-04)
# Nike's Q1 FY2027 earnings release (8-K filed 2026-10-01, accession 0000320187-26-000184,
# Exhibit 99.1, saved in data/raw/8k/) guides FY2027 revenue down "high-single digits",
# a mid-20s tax rate and adjusted diluted EPS of USD 1.15-1.35. The base case above
# (FY2027 -1.1%, margin 9.1%) predates that guidance; these scenarios start from it.
# ---------------------------------------------------------------------------
GUIDANCE_FY2027 = {
    "value": {"revenue_growth_low": -0.09, "revenue_growth_high": -0.07,
              "adjusted_eps_low": 1.15, "adjusted_eps_high": 1.35, "tax_rate": 0.25},
    "unit": "fractions; EPS in USD per diluted share",
    "source": ("Nike Q1 FY2027 earnings release, Outlook section (8-K 0000320187-26-000184, Ex. 99.1, 2026-10-01). "
               "'High-single digits' read as -7% to -9% and 'mid-20 percent range' as 25%: judgment"),
    "date_set": "2026-10-04",
}

NON_OPERATING_INCOME_FY2027 = {
    "value": 103.0,
    "unit": "USD millions (pre-tax income minus operating income)",
    "source": "FY2026 actual: pre-tax income 3,900 - (gross profit - S&A) 3,797 (output/02_historical_metrics.csv); judgment that FY2027 is similar",
    "date_set": "2026-10-04",
}

MEMO_SCENARIOS = {
    "value": {
        "Bear": {"growth": [-0.08, 0.00, 0.02, 0.02, 0.02], "margin_fy2031": 0.075},
        "Base": {"growth": [-0.08, 0.03, 0.04, 0.04, 0.04], "margin_fy2031": 0.105},
        "Bull": {"growth": [-0.08, 0.05, 0.06, 0.06, 0.05], "margin_fy2031": 0.125},
    },
    "unit": "revenue growth FY2027-FY2031 (fractions); operating margin reached in FY2031, straight line from the FY2027 guidance margin",
    "source": ("judgment for the memo. FY2027 = guidance midpoint (-8%). Bear: no recovery beyond the FY2025-26 trough margin. "
               "Base: half-way-plus back, helped by Pace's USD 2.5bn cumulative savings through FY2031 (8-K). "
               "Bull: full return to the FY2017-24 average 12.5% margin and growth near the FY2016-24 CAGR of 5.9%"),
    "date_set": "2026-10-04",
}
