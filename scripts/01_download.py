"""
01_download.py  -  Download Nike's annual financials (SEC) and daily stock prices (Yahoo)

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
1. Asks the SEC's EDGAR "company facts" API for every number Nike has ever tagged
   in its filings. That is one big JSON file. We save it to data/raw/ exactly as
   downloaded, so we can always go back to the original.
2. From that file, keeps only numbers that came from annual reports (10-K) and that
   cover a full fiscal year, then picks out the ten items we care about (revenue,
   gross profit, operating income, net income, D&A, capex, operating cash flow,
   debt, cash, shares) for the last 10 fiscal years.
3. Downloads Nike's daily stock prices from Yahoo Finance (via the yfinance
   library) for the same 10-year window, and saves that raw table to data/raw/ too.
   Prices are the one non-SEC input here; SEC does not publish stock prices.
4. Writes everything to one Excel workbook in data/processed/, one tab per dataset,
   plus a "sources" tab that says which filing every single number came from and
   a "data_quality" tab listing anything that did not come through cleanly.

WHY IT IS BUILT THIS WAY
------------------------
- SEC data is the source of truth for financials (project rule 2), so financials
  come ONLY from EDGAR.
- Every number keeps its receipt: form type, accession number, filed date, and
  the XBRL tag it was reported under. Nothing is typed in by hand.
- The only arithmetic in this script is (a) dividing by 1,000,000 to show USD
  millions, and (b) two clearly labelled sums (EBIT if Nike doesn't report
  operating income, and total debt). Both show their parts in their own columns.
- No modeling assumptions live here. The settings below (which company, how many
  years, where to save) are download settings, not model inputs.

HOW TO RUN
----------
    python3 scripts/01_download.py

The SEC asks every program that calls its API to identify itself with a
"User-Agent" (a name plus contact email). Set your own with an environment
variable before running, e.g.
    export SEC_USER_AGENT="nike-valuation-project you@example.com"
"""

import json
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# DOWNLOAD SETTINGS (not modeling assumptions; those live in assumptions.py)
# ---------------------------------------------------------------------------
CIK = "0000320187"          # Nike's permanent ID number at the SEC
TICKER = "NKE"              # Nike's stock ticker, used for the price download
N_YEARS = 10                # how many fiscal years of financials to keep

# The SEC wants a descriptive name + contact. Override with the SEC_USER_AGENT
# environment variable (recommended: put your own email in it).
USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", "nike-valuation-project personal-research"
)

# Folder locations. PROJECT is the folder that holds data/, scripts/, output/.
PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"
PROCESSED = PROJECT / "data" / "processed"
TODAY = date.today().isoformat()

COMPANYFACTS_URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"

# ---------------------------------------------------------------------------
# WHICH XBRL TAGS TO LOOK FOR
# ---------------------------------------------------------------------------
# Companies label each number with a standard "tag" (like a column name). The
# same idea can be filed under different tags in different years, so for each
# item we list tags in order of preference. For each year we use the first tag
# that has a value, and the sources tab records which one was used.
#
# kind = "duration": the number covers a period (e.g. revenue for the year)
# kind = "instant":  the number is a snapshot on one date (e.g. cash on May 31)
METRICS = {
    "revenue": {
        "label": "Revenue (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["Revenues",
                 "RevenueFromContractWithCustomerExcludingAssessedTax",
                 "SalesRevenueNet"],
    },
    "gross_profit": {
        "label": "Gross profit (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["GrossProfit"],
    },
    "sga": {
        # Nike's "Total selling and administrative expense" (demand creation +
        # operating overhead). Used to build operating income, because Nike
        # does not report an operating income line.
        "label": "Selling & administrative expense (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["SellingGeneralAndAdministrativeExpense"],
    },
    "operating_income": {
        "label": "Operating income (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["OperatingIncomeLoss"],
    },
    "pretax_income": {
        # Used to build EBIT if Nike doesn't tag operating income (it presents
        # "Income before income taxes" and "Interest expense (income), net").
        "label": "Income before income taxes (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                 "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    },
    "interest_expense_net": {
        # Positive = net interest EXPENSE. Tags where the company reports net
        # interest INCOME as positive are flipped (see SIGN_FLIP below).
        "label": "Interest expense (income), net (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["InterestExpenseNonoperating",
                 "InterestIncomeExpenseNonoperatingNet",
                 "InterestIncomeExpenseNet",
                 "InterestExpense"],
    },
    "net_income": {
        "label": "Net income (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["NetIncomeLoss"],
    },
    "d_and_a": {
        "label": "Depreciation & amortization (USD millions)",
        "kind": "duration", "unit": "USD",
        # Nike's cash flow statement line was tagged "Depreciation" through
        # FY2024 and "DepreciationDepletionAndAmortization" from FY2023 on (the
        # two agree for FY2023-24, so it is the same line under a new tag). The
        # sources tab shows which tag each year used.
        "tags": ["DepreciationDepletionAndAmortization",
                 "DepreciationAmortizationAndAccretionNet",
                 "DepreciationAndAmortization",
                 "Depreciation"],
    },
    "capex": {
        "label": "Capital expenditures (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["PaymentsToAcquirePropertyPlantAndEquipment",
                 "PaymentsToAcquireProductiveAssets"],
    },
    "operating_cash_flow": {
        "label": "Operating cash flow (USD millions)",
        "kind": "duration", "unit": "USD",
        "tags": ["NetCashProvidedByUsedInOperatingActivities",
                 "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    },
    "long_term_debt_noncurrent": {
        "label": "Long-term debt, non-current (USD millions)",
        "kind": "instant", "unit": "USD",
        "tags": ["LongTermDebtNoncurrent"],
    },
    "long_term_debt_current": {
        "label": "Current portion of long-term debt (USD millions)",
        "kind": "instant", "unit": "USD",
        "tags": ["LongTermDebtCurrent"],
    },
    "notes_payable": {
        "label": "Notes payable / short-term borrowings (USD millions)",
        "kind": "instant", "unit": "USD",
        "tags": ["ShortTermBorrowings", "NotesPayableCurrent",
                 "CommercialPaper"],
    },
    "cash": {
        "label": "Cash and equivalents (USD millions)",
        "kind": "instant", "unit": "USD",
        "tags": ["CashAndCashEquivalentsAtCarryingValue"],
    },
    "short_term_investments": {
        "label": "Short-term investments (USD millions)",
        "kind": "instant", "unit": "USD",
        # Nike changed the tag for this line twice (FY2017, FY2018-21, FY2021+).
        "tags": ["ShortTermInvestments",
                 "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent",
                 "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
                 "AvailableForSaleSecuritiesCurrent"],
    },
    "shares_diluted_weighted": {
        "label": "Diluted weighted-average shares (millions)",
        "kind": "duration", "unit": "shares",
        "tags": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    },
    "shares_basic_weighted": {
        "label": "Basic weighted-average shares (millions)",
        "kind": "duration", "unit": "shares",
        "tags": ["WeightedAverageNumberOfSharesOutstandingBasic"],
    },
    "shares_outstanding_year_end": {
        # Nike has Class A and Class B shares. If it only tags them by class,
        # the company facts API (which drops by-class detail) will have no total,
        # and this column will be blank; the weighted averages above still work.
        "label": "Shares outstanding at year end (millions)",
        "kind": "instant", "unit": "shares",
        "tags": ["CommonStockSharesOutstanding"],
    },
}

# Tags where a positive number means interest INCOME, so we multiply by -1 to
# keep "positive = expense" consistent in the interest_expense_net column.
SIGN_FLIP = {"InterestIncomeExpenseNonoperatingNet", "InterestIncomeExpenseNet"}

# A fiscal year is roughly 365 days; Nike's years end on May 31 and are always
# 365 or 366 days. Anything outside this window is a quarter or a partial period.
FULL_YEAR_DAYS = (350, 380)

ANNUAL_FORMS = {"10-K", "10-K/A"}


# ---------------------------------------------------------------------------
# STEP 1: download the SEC file and save it untouched
# ---------------------------------------------------------------------------
def download_companyfacts():
    """Fetch Nike's company facts JSON from EDGAR, save the exact bytes to
    data/raw/, and return it as a Python dictionary."""
    print(f"Downloading {COMPANYFACTS_URL}")
    resp = requests.get(COMPANYFACTS_URL, headers={"User-Agent": USER_AGENT},
                        timeout=60)
    resp.raise_for_status()  # stop with an error if the SEC refused the request

    RAW.mkdir(parents=True, exist_ok=True)
    raw_path = RAW / f"companyfacts_CIK{CIK}_{TODAY}.json"
    raw_path.write_bytes(resp.content)  # the bytes exactly as received
    print(f"  saved raw file: {raw_path}")
    return json.loads(resp.content)


# ---------------------------------------------------------------------------
# STEP 2: pick annual numbers out of the SEC file
# ---------------------------------------------------------------------------
def annual_facts_for_tag(facts, tag, kind, unit):
    """Return a table of every 10-K value reported under one tag.

    The SEC file lists each number once per filing it appeared in, so a 2020
    revenue figure shows up in the FY2020, FY2021 and FY2022 10-Ks (as the
    comparison columns). We keep all of them for now and choose later.
    """
    entries = (facts.get("facts", {}).get("us-gaap", {})
               .get(tag, {}).get("units", {}).get(unit, []))
    if not entries:
        return pd.DataFrame()

    df = pd.DataFrame(entries)
    df = df[df["form"].isin(ANNUAL_FORMS)].copy()   # annual reports only
    if df.empty:
        return df

    df["end"] = pd.to_datetime(df["end"])
    if kind == "duration":
        # keep only values that span a full year (drops quarters, e.g. Q4 alone)
        df["start"] = pd.to_datetime(df["start"])
        days = (df["end"] - df["start"]).dt.days
        df = df[days.between(*FULL_YEAR_DAYS)].copy()
    else:
        # snapshots: keep only the fiscal year-end date (May 31-ish),
        # not e.g. the opening balance of an earlier year
        df = df[df["end"].dt.month.isin([5, 6])].copy()
        df["start"] = pd.NaT

    # Nike's fiscal year is named after the calendar year it ends in:
    # the year ending May 31, 2025 is FY2025.
    df["fiscal_year"] = df["end"].dt.year
    df["tag"] = tag
    return df


def pick_metric(facts, key, spec):
    """For one metric, return one row per fiscal year with the chosen value and
    its source filing, plus a list of data-quality notes."""
    rows, notes = [], []
    tag_tables = [(t, annual_facts_for_tag(facts, t, spec["kind"], spec["unit"]))
                  for t in spec["tags"]]
    all_years = sorted({fy for _, d in tag_tables if not d.empty
                        for fy in d["fiscal_year"]})

    for fy in all_years:
        for tag, d in tag_tables:          # first tag (in preference order) wins
            if d.empty:
                continue
            cands = d[d["fiscal_year"] == fy]
            if cands.empty:
                continue
            # Several filings may report this year. Use the most recently filed
            # one: if Nike later restated the number, that is the corrected value.
            cands = cands.sort_values("filed")
            chosen = cands.iloc[-1]
            distinct = sorted(float(v) for v in cands["val"].unique())
            if len(distinct) > 1:
                notes.append((int(fy),
                    f"{key} FY{fy}: filings disagree ({', '.join(f'{v:,.0f}' for v in distinct)}); used the latest "
                    f"filed ({chosen['form']} filed {chosen['filed']}, "
                    f"accn {chosen['accn']})."))
            val = float(chosen["val"])
            if tag in SIGN_FLIP:
                val = -val
            rows.append({
                "metric": key,
                "label": spec["label"],
                "fiscal_year": int(fy),
                "value_raw": val,                     # in USD or shares
                "unit": spec["unit"],
                "xbrl_tag": tag,
                "sign_flipped": tag in SIGN_FLIP,
                "form": chosen["form"],
                "accession_number": chosen["accn"],
                "filed": chosen["filed"],
                "period_start": (chosen["start"].date()
                                 if pd.notna(chosen["start"]) else None),
                "period_end": chosen["end"].date(),
                "n_filings_reporting_this_year": len(cands),
            })
            break
    return rows, notes


def build_financials(facts):
    """Run pick_metric for every metric, keep the last N_YEARS fiscal years, and
    return (sources table, wide annual table, data-quality notes)."""
    all_rows, notes = [], []
    for key, spec in METRICS.items():
        rows, n = pick_metric(facts, key, spec)
        all_rows += rows
        notes += n   # (fiscal_year, note) pairs, filtered to kept years below
        if not rows:
            notes.append(f"{key}: no 10-K values found under any of "
                         f"{spec['tags']}.")

    sources = pd.DataFrame(all_rows)

    # The last 10 fiscal years = the 10 most recent years that have revenue.
    rev_years = sorted(sources.loc[sources.metric == "revenue", "fiscal_year"])
    keep_years = rev_years[-N_YEARS:]
    sources = sources[sources.fiscal_year.isin(keep_years)].reset_index(drop=True)
    # Keep only notes about the years we kept (plain-text notes have no year).
    notes = [n if isinstance(n, str) else n[1] for n in notes
             if isinstance(n, str) or n[0] in keep_years]

    # Show money and share counts in millions (the only scaling we do).
    sources["value_millions"] = sources["value_raw"] / 1_000_000

    # Wide table: one row per fiscal year, one column per metric.
    wide = (sources.pivot(index="fiscal_year", columns="label",
                          values="value_millions")
            .reindex(keep_years))
    ordered = [METRICS[k]["label"] for k in METRICS
               if METRICS[k]["label"] in wide.columns]
    wide = wide[ordered]

    # Flag gaps: any metric missing for any of the kept years.
    for key, spec in METRICS.items():
        col = spec["label"]
        if col not in wide.columns:
            continue
        missing = [fy for fy in keep_years if pd.isna(wide.loc[fy, col])]
        if missing:
            notes.append(f"{key}: no value for FY{', FY'.join(map(str, missing))}.")

    wide = add_derived_columns(wide, notes)
    wide.index.name = "Fiscal year (ends May 31)"
    return sources, wide, notes


def add_derived_columns(wide, notes):
    """Add the two visible sums. Each one's parts sit in their own columns, and
    the formula is written in the column name."""
    L = {k: v["label"] for k, v in METRICS.items()}

    # Operating income: Nike doesn't tag OperatingIncomeLoss, so build it the
    # way its income statement is laid out: gross profit - selling & admin.
    op = L["operating_income"]
    if op not in wide.columns or wide[op].isna().all():
        if L["gross_profit"] in wide.columns and L["sga"] in wide.columns:
            col = ("Operating income = gross profit - selling & administrative "
                   "expense (USD millions)")
            wide[col] = wide[L["gross_profit"]] - wide[L["sga"]]
            notes.append(
                "operating_income: Nike does not report an operating income "
                "line, so it is built as gross profit - total selling & "
                "administrative expense. It excludes interest and 'Other "
                "(income) expense, net'.")

    # EBIT (Nike's own non-GAAP definition): only if operating income wasn't tagged.
    if op not in wide.columns or wide[op].isna().all():
        if L["pretax_income"] in wide.columns and L["interest_expense_net"] in wide.columns:
            col = ("EBIT = income before taxes + interest expense (income), net "
                   "(USD millions)")
            wide[col] = wide[L["pretax_income"]] + wide[L["interest_expense_net"]]
            notes.append(
                "EBIT: built as income before taxes + net interest expense "
                "(Nike's own EBIT definition). Unlike operating income above, "
                "it includes Nike's 'Other (income) expense, net' line.")

    # Total debt = non-current long-term debt + current portion + notes payable.
    # (Excludes operating lease liabilities.) Blank parts count as zero, but a
    # note is written for every blank so nothing is silently assumed.
    parts = [L["long_term_debt_noncurrent"], L["long_term_debt_current"],
             L["notes_payable"]]
    present = [p for p in parts if p in wide.columns]
    if present:
        col = ("Total debt = LT debt non-current + current portion + notes "
               "payable (USD millions, excl. leases)")
        wide[col] = wide[present].fillna(0).sum(axis=1)
        for p in parts:
            if p not in wide.columns:
                notes.append(f"total debt: '{p}' not found in any year; counted as 0.")
            else:
                blank = wide.index[wide[p].isna()].tolist()
                if blank:
                    notes.append(f"total debt: '{p}' blank for FY{blank}; counted as 0.")
    return wide


# ---------------------------------------------------------------------------
# STEP 3: daily stock prices (non-SEC)
# ---------------------------------------------------------------------------
def download_prices(first_fiscal_year):
    """Download daily NKE prices from Yahoo Finance starting at the beginning of
    the first fiscal year we kept (June 1 of the prior calendar year)."""
    start = f"{first_fiscal_year - 1}-06-01"
    print(f"Downloading {TICKER} daily prices from Yahoo Finance since {start}")
    # auto_adjust=False keeps BOTH the actual closing price ("Close") and the
    # dividend- and split-adjusted price ("Adj Close").
    px = yf.Ticker(TICKER).history(start=start, auto_adjust=False)
    if px.empty:
        raise RuntimeError("Yahoo Finance returned no price data.")
    px.index = px.index.tz_localize(None)   # Excel can't store time zones
    px.index.name = "Date"

    RAW.mkdir(parents=True, exist_ok=True)
    raw_path = RAW / f"{TICKER}_daily_prices_yfinance_{TODAY}.csv"
    px.to_csv(raw_path)
    print(f"  saved raw file: {raw_path}")

    px = px.rename(columns={c: f"{c} (USD)" for c in
                            ["Open", "High", "Low", "Close", "Adj Close",
                             "Dividends"]})
    px = px.rename(columns={"Volume": "Volume (shares)",
                            "Stock Splits": "Stock split ratio"})
    return px


# ---------------------------------------------------------------------------
# STEP 4: write the Excel workbook
# ---------------------------------------------------------------------------
def write_workbook(wide, sources, notes, prices):
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / f"nike_financials_and_prices_{TODAY}.xlsx"

    readme = pd.DataFrame({"Item": [
        "Created", "Financials source", "Prices source", "Fiscal year",
        "Units", "Which value when filings disagree", "Tabs"],
        "Detail": [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        f"SEC EDGAR company facts API, {COMPANYFACTS_URL} (10-K filings only)",
        f"Yahoo Finance via yfinance ({TICKER}), NOT SEC data",
        "Nike's fiscal year ends May 31; FY2025 = Jun 2024 to May 2025",
        "USD millions; share counts in millions; prices in USD per share",
        "Most recently filed 10-K value (picks up restatements); see data_quality",
        "financials_annual, financials_sources, data_quality, stock_prices_daily",
    ]})

    quality = pd.DataFrame({"Note": notes or ["No issues found."]})

    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        readme.to_excel(xl, sheet_name="README", index=False)
        wide.to_excel(xl, sheet_name="financials_annual")
        sources.to_excel(xl, sheet_name="financials_sources", index=False)
        quality.to_excel(xl, sheet_name="data_quality", index=False)
        prices.to_excel(xl, sheet_name="stock_prices_daily")

        # cosmetic only: widen columns so headers are readable
        for ws in xl.book.worksheets:
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0
                            for c in col[:50])
                ws.column_dimensions[col[0].column_letter].width = min(width + 2, 60)
            ws.freeze_panes = "B2"
    print(f"Saved workbook: {path}")
    return path


def main():
    facts = download_companyfacts()
    sources, wide, notes = build_financials(facts)
    prices = download_prices(int(wide.index.min()))
    write_workbook(wide, sources, notes, prices)
    print("\nData-quality notes:")
    for n in notes:
        print(" -", n)


if __name__ == "__main__":
    main()
