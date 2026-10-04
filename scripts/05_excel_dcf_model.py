"""
05_excel_dcf_model.py  -  Build a 5-year DCF model of Nike as an Excel workbook with live formulas

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
Scripts 01-04 did the work in Python. This script lays the same work out in
Excel so every calculation can be seen and changed in a cell. It does NOT
type in results: almost every number you see in the workbook is an Excel
formula (e.g. "=C7*(1+D6)"), so if you change an assumption in Excel, the whole
model updates.

The workbook has these tabs, in the order money flows through them:

    README       - how the tabs connect, and the colour code
    Assumptions  - EVERY input in one place: forecast drivers, market data
                   (price, interest rate, beta...), and the latest balance sheet.
                   Each row has a value, unit, source and the date it was set.
    Historicals  - Nike's FY2017-FY2026 figures from the 10-Ks, plus ratios
                   (growth, margins, capex % of revenue...) computed by formula.
    Sources      - the SEC filing (form, accession number, date) behind every
                   historical number.
    WACC         - the discount rate, built step by step from Assumptions.
    Forecast     - FY2027-FY2031: revenue, margins, taxes, D&A, capex, working
                   capital, and free cash flow to the firm (FCFF).
    Valuation    - discounts each year's FCFF, adds a terminal value, then goes
                   from enterprise value to equity value per share and compares
                   it with today's price. Includes a WACC x growth sensitivity table.

Where the numbers come from (project rules 2 and 3):
  - Historical figures: data/processed/nike_financials_and_prices_2026-10-04.xlsx
    and output/02_historical_metrics.csv (both built from SEC 10-K data), plus
    working-capital lines read here from the raw SEC company-facts file.
  - Every modeling input: scripts/assumptions.py. The Assumptions tab is a copy
    of those values. If you experiment in Excel, the workbook changes but
    assumptions.py does not; to make a change official, edit assumptions.py and
    re-run this script.

After building the file, the script asks LibreOffice to open and recalculate it
(so the saved file contains computed values, and we can check there are no
formula errors), then saves the computed Forecast and Valuation tables as CSV
in output/ (project rule 4).

HOW TO RUN
----------
    python3 scripts/05_excel_dcf_model.py
Needs: pandas, openpyxl, and LibreOffice ("soffice") for the recalculation step.
"""

import json
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

import assumptions as A

# ---------------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
PROCESSED_XLSX = ROOT / "data/processed/nike_financials_and_prices_2026-10-04.xlsx"
HIST_CSV = ROOT / "output/02_historical_metrics.csv"
EXTRA_SOURCES_CSV = ROOT / "output/02_extra_sec_inputs_sources.csv"
LATEST_BS_CSV = ROOT / "output/04_latest_balance_sheet_and_shares.csv"
COMPANYFACTS = ROOT / "data/raw/companyfacts_CIK0000320187_2026-10-04.json"
OUT_XLSX = ROOT / "output/05_nike_dcf_model.xlsx"
OUT_FORECAST_CSV = ROOT / "output/05_forecast.csv"
OUT_VALUATION_CSV = ROOT / "output/05_valuation.csv"
OUT_SENS_CSV = ROOT / "output/05_sensitivity_value_per_share_usd.csv"

YEARS = list(range(2017, 2027))                    # historical fiscal years
BASE_FY = A.BASE_FISCAL_YEAR["value"]              # 2026
N_FC = A.EXCEL_FORECAST_YEARS["value"]             # 5
FC_YEARS = list(range(BASE_FY + 1, BASE_FY + 1 + N_FC))   # 2027..2031

# ---------------------------------------------------------------------------
# Look and feel. Standard financial-model colour code:
#   blue text  = a number typed in (an input or a historical fact)
#   black text = a formula calculated on the same tab
#   green text = a formula that pulls a number from another tab
# ---------------------------------------------------------------------------
BLUE = Font(color="0000CC")
BLACK = Font(color="000000")
GREEN = Font(color="007A33")
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14)
HEADER_FILL = PatternFill("solid", fgColor="DDE4EE")
INPUT_FILL = PatternFill("solid", fgColor="FFF7D6")     # pale yellow behind inputs
KEY_FILL = PatternFill("solid", fgColor="E2F0D9")       # pale green behind key results
THIN = Side(style="thin", color="999999")
TOP_BORDER = Border(top=THIN)

FMT_USD_M = '#,##0;(#,##0);"-"'          # USD millions, negatives in brackets
FMT_USD_M1 = '#,##0.0;(#,##0.0);"-"'
FMT_PCT = '0.0%;(0.0%);"-"'
FMT_PCT2 = '0.00%;(0.00%);"-"'
FMT_USD = '$#,##0.00'
FMT_NUM2 = '0.00'
FMT_NUM4 = '0.0000'
FMT_DATE = 'yyyy-mm-dd'


def link_font(formula, this_sheet):
    """Green if the formula uses a cell from another tab (by sheet reference or by name), else black."""
    if re.search(r"[A-Za-z]+!", formula):
        return GREEN
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula))
    return GREEN if any(NAME_SHEET.get(w, this_sheet) != this_sheet for w in words) else BLACK


def style_header_row(ws, row, ncols):
    """Grey-blue background and bold text across a header row."""
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = BOLD
        cell.alignment = Alignment(wrap_text=True, vertical="center")


NAME_SHEET = {}     # Excel name -> the tab it lives on (used to colour cross-tab formulas green)


def add_name(wb, name, sheet, cell_ref):
    """Give a cell a readable name (e.g. 'WACC') so formulas read like words."""
    NAME_SHEET[name] = sheet
    col, row = cell_ref
    ref = f"'{sheet}'!${get_column_letter(col)}${row}"
    wb.defined_names[name] = DefinedName(name, attr_text=ref)


# ---------------------------------------------------------------------------
# STEP 1. Load the historical data built by earlier scripts
# ---------------------------------------------------------------------------
fin = pd.read_excel(PROCESSED_XLSX, sheet_name="financials_annual").set_index("Fiscal year (ends May 31)")
hist = pd.read_csv(HIST_CSV).set_index("Fiscal year (ends May 31)")
fin_sources = pd.read_excel(PROCESSED_XLSX, sheet_name="financials_sources")
extra_sources = pd.read_csv(EXTRA_SOURCES_CSV)
latest_bs = pd.read_csv(LATEST_BS_CSV).set_index("item")

# Working-capital lines are not in the earlier tables, so read them from the
# raw SEC company-facts file. Rule (same as script 01): for each fiscal
# year-end (May 31), take the value from the most recently filed 10-K.
facts = json.loads(COMPANYFACTS.read_text())["facts"]["us-gaap"]
NWC_TAGS = {
    "receivables": ("Accounts receivable, net (USD m)", "AccountsReceivableNetCurrent"),
    "inventories": ("Inventories (USD m)", "InventoryFinishedGoodsNetOfReserves"),
    "prepaid": ("Prepaid expenses and other current assets (USD m)", "PrepaidExpenseAndOtherAssetsCurrent"),
    "payables": ("Accounts payable (USD m)", "AccountsPayableCurrent"),
    "accrued": ("Accrued liabilities (USD m)", "AccruedLiabilitiesCurrent"),
}
nwc_values, nwc_source_rows = {}, []
for key, (label, tag) in NWC_TAGS.items():
    best = {}
    for fact in facts[tag]["units"]["USD"]:
        is_year_end_10k = fact.get("form") == "10-K" and fact["end"].endswith("-05-31")
        if not is_year_end_10k:
            continue
        fy = int(fact["end"][:4])
        if fy in YEARS and (fy not in best or fact["filed"] > best[fy]["filed"]):
            best[fy] = fact
    missing = [y for y in YEARS if y not in best]
    if missing:
        raise SystemExit(f"{tag}: no 10-K value for {missing}")
    nwc_values[key] = {y: best[y]["val"] / 1e6 for y in YEARS}
    for y in YEARS:
        f = best[y]
        nwc_source_rows.append([label, y, f["val"] / 1e6, tag, f["form"], f["accn"], f["filed"], f["end"]])

# The DCF in scripts/dcf_model.py starts from script 02's working capital; make sure
# both read the same SEC numbers.
nwc_02 = hist["Operating working capital = AR + inventories + prepaid - AP - accrued (USD m)"]
for y in YEARS:
    ours = (nwc_values["receivables"][y] + nwc_values["inventories"][y] + nwc_values["prepaid"][y]
            - nwc_values["payables"][y] - nwc_values["accrued"][y])
    assert abs(ours - nwc_02[y]) < 0.01, f"working capital FY{y} differs from script 02"

# ---------------------------------------------------------------------------
# STEP 2. Create the workbook and the README tab
# ---------------------------------------------------------------------------
wb = Workbook()
ws_readme = wb.active
ws_readme.title = "README"

# ---------------------------------------------------------------------------
# STEP 3. Assumptions tab: every input, with unit, source and date set
# ---------------------------------------------------------------------------
ws_a = wb.create_sheet("Assumptions")
ws_a["A1"] = "Assumptions: every input to the model lives on this tab"
ws_a["A1"].font = TITLE
ws_a["A2"] = ("Blue numbers on a yellow background are inputs: change them here and the whole model updates. "
              "Official copy: scripts/assumptions.py (re-run scripts/05_excel_dcf_model.py to rebuild).")
headers = ["Input", "Value", "Unit", "Source", "Date set", "Name used in formulas"]
ws_a.append([])
ws_a.append(headers)
style_header_row(ws_a, 4, len(headers))

latest_src = latest_bs.loc["Cash and equivalents (USD m)"]
q1_source = f"SEC {latest_src['form']} for the quarter ended {latest_src['period_end']}, accession {latest_src['accession_number']}, filed {latest_src['filed']}"


def a_section(title):
    ws_a.append([title])
    ws_a.cell(row=ws_a.max_row, column=1).font = BOLD


def a_input(name, label, value, unit, source, date_set, fmt):
    """One input row. 'name' becomes an Excel name, so other tabs can write =WACC etc."""
    ws_a.append([label, value, unit, source, date_set, name])
    r = ws_a.max_row
    cell = ws_a.cell(row=r, column=2)
    cell.font, cell.fill, cell.number_format = BLUE, INPUT_FILL, fmt
    add_name(wb, name, "Assumptions", (2, r))
    return r


def from_py(name, label, a, fmt, value=None):
    """Input row copied from an assumptions.py entry (value, unit, source, date_set)."""
    return a_input(name, label, a["value"] if value is None else value, a["unit"], a["source"], a["date_set"], fmt)


a_section("1. Valuation setup")
from_py("Valuation_Date", "Valuation date (share price date)", A.VALUATION_DATE, FMT_DATE,
        value=date.fromisoformat(A.VALUATION_DATE["value"]))
from_py("Base_FY", "Base year (last actual fiscal year)", A.BASE_FISCAL_YEAR, "0")
from_py("Share_Of_FY2027_Remaining", "Share of FY2027 cash flow still to come", A.SHARE_OF_FY2027_REMAINING, "0%")

a_section("2. Revenue growth by year (forecast)")
for fy in FC_YEARS:
    from_py(f"Growth_FY{fy}", f"Revenue growth FY{fy}", A.EXCEL_REVENUE_GROWTH, FMT_PCT,
            value=A.EXCEL_REVENUE_GROWTH["value"][fy])
from_py("Growth_Adjustment", "Growth adjustment added to FY2028-31 (scenario testing, 0 = base case; FY2027 stays at guidance)",
        A.EXCEL_GROWTH_ADJUSTMENT, FMT_PCT2)

a_section("3. Margins, tax and reinvestment (forecast)")
from_py("FY2027_Margin", "FY2027 operating margin (from Nike's guidance)", A.FY2027_OPERATING_MARGIN, FMT_PCT2)
from_py("Target_Margin", "Target operating margin", A.TARGET_OPERATING_MARGIN, FMT_PCT)
from_py("Years_To_Target", "Years after FY2026 to reach the target margin (straight line from FY2027's guidance margin)",
        A.YEARS_TO_REACH_TARGET_MARGIN, "0")
from_py("Tax_Rate", "Tax rate on operating income", A.FORECAST_TAX_RATE, FMT_PCT)
from_py("DA_Pct", "Depreciation & amortization, % of revenue", A.DA_PCT_OF_REVENUE, FMT_PCT2)
from_py("Capex_Pct", "Capital expenditures, % of revenue", A.CAPEX_PCT_OF_REVENUE, FMT_PCT2)
from_py("NWC_Pct", "Operating working capital, % of revenue", A.NWC_PCT_OF_REVENUE, FMT_PCT)

a_section("4. Terminal value")
from_py("Terminal_Growth", "Cash flow growth forever after FY2031", A.TERMINAL_GROWTH, FMT_PCT)

a_section("5. Market inputs for the discount rate (NOT from the SEC)")
from_py("Share_Price", "Share price (USD)", A.SHARE_PRICE, FMT_USD)
from_py("Risk_Free", "Risk-free rate (10-year US Treasury yield)", A.RISK_FREE_RATE, FMT_PCT2)
from_py("Nike_Beta", "Beta (how much Nike's stock moves with the market)", A.BETA, "0.000")
from_py("ERP", "Equity risk premium", A.EQUITY_RISK_PREMIUM, FMT_PCT2)
from_py("Debt_Spread", "Nike's borrowing spread over the risk-free rate", A.PRETAX_COST_OF_DEBT_SPREAD, FMT_PCT2)
from_py("Tax_On_Interest", "Tax rate saved on interest", A.TAX_RATE_ON_INTEREST, FMT_PCT)

a_section("6. Latest balance sheet and shares (SEC Q1 FY2027 10-Q, 2026-08-31)")
bs_rows = [
    ("Cash", "Cash and equivalents (USD m)", "Cash and equivalents (USD m)"),
    ("ST_Investments", "Short-term investments (USD m)", "Short-term investments (USD m)"),
    ("Debt_LT_Noncurrent", "Long-term debt, non-current (USD m)", "Long-term debt, non-current (USD m)"),
    ("Debt_LT_Current", "Current portion of long-term debt (USD m)", "Current portion of long-term debt (USD m)"),
    ("Debt_Short_Term", "Notes payable / short-term borrowings (USD m)", "Notes payable / short-term borrowings (USD m)"),
]
for name, label, key in bs_rows:
    row = latest_bs.loc[key]
    src = q1_source + f", XBRL tag {row['xbrl_tag']}"
    if isinstance(row["note"], str) and row["note"]:
        src = f"{row['note']} (XBRL tag {row['xbrl_tag']})"
    a_input(name, label, float(row["value"]), "USD millions", src, "2026-10-04", FMT_USD_M)
shares_row = latest_bs.loc["Diluted weighted-average shares, latest quarter (millions)"]
a_input("Shares", "Diluted shares (weighted average for the quarter)", float(shares_row["value"]), "millions",
        q1_source + ", XBRL tag WeightedAverageNumberOfDilutedSharesOutstanding. "
        "Weighted average, not the exact 2026-08-31 count, which the SEC data file lacks", "2026-10-04", "#,##0.0")

a_section("7. Presentation only")
from_py("Sens_WACC_Step", "Sensitivity table: WACC step", A.SENSITIVITY_WACC_STEP, FMT_PCT2)
from_py("Sens_Growth_Step", "Sensitivity table: terminal growth step", A.SENSITIVITY_GROWTH_STEP, FMT_PCT2)

for col, width in zip("ABCDEF", [58, 13, 34, 90, 11, 22]):
    ws_a.column_dimensions[col].width = width
for row in ws_a.iter_rows(min_row=5):
    row[3].alignment = Alignment(wrap_text=True, vertical="top")
    row[2].alignment = Alignment(wrap_text=True, vertical="top")
ws_a.freeze_panes = "A5"

# ---------------------------------------------------------------------------
# STEP 4. Historicals tab: SEC figures (blue) + ratios (formulas)
# Layout: one row per line item, one column per fiscal year (B=FY2017 ... K=FY2026),
# then L = FY2017-26 average and M = FY2022-26 average for the ratio rows.
# ---------------------------------------------------------------------------
ws_h = wb.create_sheet("Historicals")
ws_h["A1"] = "Historicals: Nike FY2017-FY2026 (USD millions; fiscal year ends May 31)"
ws_h["A1"].font = TITLE
ws_h["A2"] = ("Blue = number from Nike's 10-K (filing details on the Sources tab). Black = formula. "
              "Columns L and M average the ratios so you can compare them with the Assumptions tab.")
ws_h.append([])
ws_h.append(["Line item"] + [f"FY{y}" for y in YEARS] + ["Avg FY2017-26", "Avg FY2022-26", "How it is calculated"])
style_header_row(ws_h, 4, 14)
H = {}                         # line key -> row number
yc = {y: get_column_letter(2 + i) for i, y in enumerate(YEARS)}   # year -> column letter
FIRST, LAST = yc[YEARS[0]], yc[YEARS[-1]]
AVG5_FIRST = yc[2022]


def h_section(title):
    ws_h.append([title])
    ws_h.cell(row=ws_h.max_row, column=1).font = BOLD


def h_data(key, label, values, note="SEC 10-K"):
    ws_h.append([label] + [values[y] for y in YEARS] + [None, None, note])
    r = ws_h.max_row
    for y in YEARS:
        c = ws_h[f"{yc[y]}{r}"]
        c.font, c.number_format = BLUE, FMT_USD_M
    H[key] = r


def h_formula(key, label, template, fmt, note, first_year=YEARS[0], average=True):
    """template uses {c} for this column and {p} for the previous year's column, {r[key]} for rows."""
    ws_h.append([label])
    r = ws_h.max_row
    for y in YEARS:
        if y < first_year:
            continue
        prev = get_column_letter(1 + YEARS.index(y)) if y > YEARS[0] else None
        c = ws_h[f"{yc[y]}{r}"]
        c.value = "=" + template.format(c=yc[y], p=prev, r=H)
        c.font, c.number_format = BLACK, fmt
    if average:
        start = yc[first_year]
        ws_h[f"L{r}"] = f"=AVERAGE({start}{r}:{LAST}{r})"
        ws_h[f"M{r}"] = f"=AVERAGE({AVG5_FIRST}{r}:{LAST}{r})"
        for col in "LM":
            ws_h[f"{col}{r}"].number_format = fmt
    ws_h[f"N{r}"] = note
    H[key] = r


col = lambda name: {y: float(fin.loc[y, name]) for y in YEARS}
h_section("Income statement")
h_data("revenue", "Revenue", col("Revenue (USD millions)"))
h_data("gross_profit", "Gross profit", col("Gross profit (USD millions)"))
h_data("sga", "Selling & administrative expense", col("Selling & administrative expense (USD millions)"))
h_formula("op_income", "Operating income", "{c}{r[gross_profit]}-{c}{r[sga]}", FMT_USD_M,
          "Gross profit - S&A (Nike reports no operating income line)", average=False)
h_data("pretax", "Income before income taxes", col("Income before income taxes (USD millions)"))
h_data("tax", "Income tax expense", {y: float(hist.loc[y, "Income tax expense (USD m)"]) for y in YEARS})
h_data("net_income", "Net income", col("Net income (USD millions)"))

h_section("Cash flow statement")
h_data("ocf", "Operating cash flow", col("Operating cash flow (USD millions)"))
h_data("da", "Depreciation & amortization", col("Depreciation & amortization (USD millions)"))
h_data("capex", "Capital expenditures", col("Capital expenditures (USD millions)"))
h_formula("fcf", "Free cash flow (simple)", "{c}{r[ocf]}-{c}{r[capex]}", FMT_USD_M,
          "Operating cash flow - capex (project definition)", average=False)

h_section("Balance sheet (at May 31)")
h_data("cash", "Cash and equivalents", col("Cash and equivalents (USD millions)"))
h_data("sti", "Short-term investments", col("Short-term investments (USD millions)"))
h_data("receivables", "Accounts receivable, net", nwc_values["receivables"])
h_data("inventories", "Inventories", nwc_values["inventories"])
h_data("prepaid", "Prepaid expenses and other current assets", nwc_values["prepaid"])
h_data("payables", "Accounts payable", nwc_values["payables"])
h_data("accrued", "Accrued liabilities", nwc_values["accrued"])
h_data("ltd", "Long-term debt, non-current", col("Long-term debt, non-current (USD millions)"))
h_data("ltd_cur", "Current portion of long-term debt", col("Current portion of long-term debt (USD millions)"))
notes = {y: (0.0 if pd.isna(fin.loc[y, "Notes payable / short-term borrowings (USD millions)"])
             else float(fin.loc[y, "Notes payable / short-term borrowings (USD millions)"])) for y in YEARS}
h_data("notes", "Notes payable / short-term borrowings", notes, "SEC 10-K (FY2026 not tagged; counted as 0)")
h_data("equity", "Shareholders' equity", {y: float(hist.loc[y, "Shareholders' equity (USD m)"]) for y in YEARS})
h_formula("nwc", "Operating working capital",
          "{c}{r[receivables]}+{c}{r[inventories]}+{c}{r[prepaid]}-{c}{r[payables]}-{c}{r[accrued]}",
          FMT_USD_M, "Receivables + inventories + prepaid - payables - accrued liabilities", average=False)
h_formula("total_debt", "Total debt (excl. leases)", "{c}{r[ltd]}+{c}{r[ltd_cur]}+{c}{r[notes]}", FMT_USD_M,
          "Sum of the three debt lines", average=False)

h_section("Ratios (all formulas)")
h_formula("growth", "Revenue growth", "{c}{r[revenue]}/{p}{r[revenue]}-1", FMT_PCT,
          "Revenue / last year's revenue - 1", first_year=2018)
h_formula("gross_margin", "Gross margin", "{c}{r[gross_profit]}/{c}{r[revenue]}", FMT_PCT, "Gross profit / revenue")
h_formula("op_margin", "Operating margin", "{c}{r[op_income]}/{c}{r[revenue]}", FMT_PCT, "Operating income / revenue")
h_formula("tax_rate", "Effective tax rate", "{c}{r[tax]}/{c}{r[pretax]}", FMT_PCT,
          "Income tax / pretax income (FY2018 includes the one-off US tax reform charge)")
h_formula("da_pct", "D&A, % of revenue", "{c}{r[da]}/{c}{r[revenue]}", FMT_PCT2, "D&A / revenue")
h_formula("capex_pct", "Capex, % of revenue", "{c}{r[capex]}/{c}{r[revenue]}", FMT_PCT2, "Capex / revenue")
h_formula("nwc_pct", "Operating working capital, % of revenue", "{c}{r[nwc]}/{c}{r[revenue]}", FMT_PCT,
          "Operating working capital / revenue")
h_formula("fcf_margin", "Free cash flow margin", "{c}{r[fcf]}/{c}{r[revenue]}", FMT_PCT, "FCF / revenue")

# Compound annual growth, a useful single number to compare with the forecast growth inputs.
ws_h.append(["Revenue growth per year, compounded FY2017-FY2024 (before the downturn)"])
r = ws_h.max_row
ws_h[f"B{r}"] = f"=({yc[2024]}{H['revenue']}/{yc[2017]}{H['revenue']})^(1/7)-1"
ws_h[f"B{r}"].number_format = FMT_PCT
ws_h[f"N{r}"] = "(FY2024 revenue / FY2017 revenue) ^ (1/7) - 1"

ws_h.column_dimensions["A"].width = 52
for c in range(2, 14):
    ws_h.column_dimensions[get_column_letter(c)].width = 11
ws_h.column_dimensions["N"].width = 70
ws_h.freeze_panes = "B5"

# ---------------------------------------------------------------------------
# STEP 5. Sources tab: the SEC filing behind each historical number
# ---------------------------------------------------------------------------
ws_s = wb.create_sheet("Sources")
ws_s["A1"] = "Sources: the SEC filing behind every historical number"
ws_s["A1"].font = TITLE
ws_s["A2"] = ("Rule: for each fiscal year, the value from the most recently filed 10-K (picks up restatements). "
              "Look up a filing on EDGAR by its accession number.")
ws_s.append([])
src_headers = ["Item", "Fiscal year", "Value (USD m)", "XBRL tag", "Form", "Accession number", "Filed", "Period end"]
ws_s.append(src_headers)
style_header_row(ws_s, 4, len(src_headers))
keep = ["revenue", "gross_profit", "sga", "pretax_income", "net_income", "operating_cash_flow", "d_and_a",
        "capex", "cash", "short_term_investments", "long_term_debt_noncurrent", "long_term_debt_current",
        "notes_payable"]
for _, s in fin_sources[fin_sources["metric"].isin(keep)].iterrows():
    ws_s.append([s["label"].replace(" (USD millions)", ""), int(s["fiscal_year"]), s["value_raw"] / 1e6,
                 s["xbrl_tag"], s["form"], s["accession_number"], s["filed"], pd.Timestamp(s["period_end"]).date().isoformat()])
for _, s in extra_sources.iterrows():
    ws_s.append([s["item"], int(s["fiscal_year"]), float(s["value_usd_millions"]), s["xbrl_tag"], s["form"],
                 s["accession_number"], s["filed"], s["period_end"]])
for row in nwc_source_rows:
    ws_s.append([row[0].replace(" (USD m)", "")] + row[1:])
for c, w in zip("ABCDEFGH", [44, 11, 14, 62, 7, 24, 12, 12]):
    ws_s.column_dimensions[c].width = w
for row in ws_s.iter_rows(min_row=5, min_col=3, max_col=3):
    row[0].number_format = FMT_USD_M
ws_s.freeze_panes = "A5"

# ---------------------------------------------------------------------------
# STEP 6. WACC tab: the discount rate, one step per row
# ---------------------------------------------------------------------------
ws_w = wb.create_sheet("WACC")
ws_w["A1"] = "WACC: the yearly return Nike's investors require (the discount rate)"
ws_w["A1"].font = TITLE
ws_w["A2"] = "Green = pulled from the Assumptions tab. Black = calculated here."
ws_w.append([])
ws_w.append(["Step", "Value", "Formula in words"])
style_header_row(ws_w, 4, 3)


def w_row(name, label, formula, fmt, words, font=BLACK, key=False):
    ws_w.append([label, formula, words])
    r = ws_w.max_row
    c = ws_w.cell(row=r, column=2)
    c.font, c.number_format = font, fmt
    if key:
        for cc in (1, 2):
            ws_w.cell(row=r, column=cc).fill = KEY_FILL
            ws_w.cell(row=r, column=cc).font = Font(bold=True, color=c.font.color.rgb if c.font.color else None)
    if name:
        add_name(wb, name, "WACC", (2, r))


ws_w.append(["Cost of equity (what shareholders expect)"]); ws_w.cell(row=ws_w.max_row, column=1).font = BOLD
w_row(None, "Risk-free rate", "=Risk_Free", FMT_PCT2, "From Assumptions", GREEN)
w_row(None, "Beta", "=Nike_Beta", "0.000", "From Assumptions", GREEN)
w_row(None, "Equity risk premium", "=ERP", FMT_PCT2, "From Assumptions", GREEN)
w_row("Cost_Of_Equity", "Cost of equity", "=Risk_Free+Nike_Beta*ERP", FMT_PCT2,
      "Risk-free rate + beta x equity risk premium (CAPM)")
ws_w.append([])
ws_w.append(["Cost of debt (what lenders charge, after the tax saving)"]); ws_w.cell(row=ws_w.max_row, column=1).font = BOLD
w_row("Pretax_Cost_Of_Debt", "Pre-tax cost of debt", "=Risk_Free+Debt_Spread", FMT_PCT2,
      "Risk-free rate + Nike's borrowing spread")
w_row("After_Tax_Cost_Of_Debt", "After-tax cost of debt", "=Pretax_Cost_Of_Debt*(1-Tax_On_Interest)", FMT_PCT2,
      "Interest is tax-deductible, so the real cost is lower: pre-tax cost x (1 - tax rate)")
ws_w.append([])
ws_w.append(["Weights (market values today)"]); ws_w.cell(row=ws_w.max_row, column=1).font = BOLD
w_row("Market_Cap", "Market value of equity (USD m)", "=Share_Price*Shares", FMT_USD_M, "Share price x diluted shares")
w_row("Total_Debt", "Debt, excl. leases (USD m)", "=Debt_LT_Noncurrent+Debt_LT_Current+Debt_Short_Term", FMT_USD_M,
      "Book value of debt from the 10-Q (used as a stand-in for its market value)")
w_row("Weight_Equity", "Weight of equity", "=Market_Cap/(Market_Cap+Total_Debt)", FMT_PCT, "Equity / (equity + debt)")
w_row("Weight_Debt", "Weight of debt", "=Total_Debt/(Market_Cap+Total_Debt)", FMT_PCT, "Debt / (equity + debt)")
ws_w.append([])
w_row("WACC", "WACC", "=Weight_Equity*Cost_Of_Equity+Weight_Debt*After_Tax_Cost_Of_Debt", FMT_PCT2,
      "Weight of equity x cost of equity + weight of debt x after-tax cost of debt", key=True)
ws_w.column_dimensions["A"].width = 44
ws_w.column_dimensions["B"].width = 14
ws_w.column_dimensions["C"].width = 80

# ---------------------------------------------------------------------------
# STEP 7. Forecast tab: FY2026 actual (column B) + FY2027-FY2031 (columns C-G)
# ---------------------------------------------------------------------------
ws_f = wb.create_sheet("Forecast")
ws_f["A1"] = "Forecast: FY2027-FY2031 (USD millions), from revenue down to free cash flow"
ws_f["A1"].font = TITLE
ws_f["A2"] = ("Column B is FY2026 actual (green, from Historicals) run through the same formulas. "
              "Columns C-G are the forecast, driven only by the Assumptions tab.")
ws_f.append([])
ws_f.append(["Line", f"FY{BASE_FY} actual"] + [f"FY{y} forecast" for y in FC_YEARS] + ["How it is calculated"])
style_header_row(ws_f, 4, 8)
fcol = {BASE_FY: "B"} | {y: get_column_letter(3 + i) for i, y in enumerate(FC_YEARS)}
NOTE_COL = get_column_letter(3 + N_FC)
F = {}
hk = yc[BASE_FY]           # FY2026 column on Historicals
hp = yc[BASE_FY - 1]       # FY2025 column on Historicals


def f_row(key, label, base, forecast, fmt, note, bold=False):
    """base: formula for FY2026 column (or None); forecast: template with {c} this col, {p} previous col."""
    ws_f.append([label])
    r = ws_f.max_row
    F[key] = r
    if base is not None:
        c = ws_f[f"B{r}"]
        c.value = base.format(r=F)
        c.font = link_font(c.value, "Forecast")
        c.number_format = fmt
    for i, y in enumerate(FC_YEARS):
        c = ws_f[f"{fcol[y]}{r}"]
        c.value = forecast.format(c=fcol[y], p=fcol[y - 1], y=y, t=i + 1, r=F)
        c.font = link_font(c.value, "Forecast")
        c.number_format = fmt
    ws_f[f"{NOTE_COL}{r}"] = note
    if bold:
        for cc in range(1, 3 + N_FC):
            ws_f.cell(row=r, column=cc).font = Font(bold=True, color=ws_f.cell(row=r, column=cc).font.color)
            ws_f.cell(row=r, column=cc).fill = KEY_FILL


f_row("year_num", "Year number (t)", "=0", "={t}", "0", "0 = FY2026, the last actual year")
f_row("growth", "Revenue growth", f"=Historicals!{hk}{H['growth']}", "=Growth_FY{y}+IF({t}=1,0,Growth_Adjustment)", FMT_PCT,
      "Growth input for that year + the scenario adjustment (Assumptions); FY2027 is Nike's guidance, no adjustment")
f_row("revenue", "Revenue", f"=Historicals!{hk}{H['revenue']}", "={p}{r[revenue]}*(1+{c}{r[growth]})", FMT_USD_M,
      "Last year's revenue x (1 + growth)")
f_row("margin", "Operating margin", f"=Historicals!{hk}{H['op_margin']}",
      "=IF({c}{r[year_num]}=1,FY2027_Margin,FY2027_Margin+(Target_Margin-FY2027_Margin)*MIN({c}{r[year_num]}-1,Years_To_Target-1)/(Years_To_Target-1))", FMT_PCT,
      "FY2027 = guidance margin; then a straight line to the target, reached in FY2031, then stays at the target")
f_row("op_income", "Operating income", "=B{r[revenue]}*B{r[margin]}", "={c}{r[revenue]}*{c}{r[margin]}", FMT_USD_M,
      "Revenue x operating margin")
f_row("taxes", "Taxes on operating income", "=B{r[op_income]}*Tax_Rate", "={c}{r[op_income]}*Tax_Rate", FMT_USD_M,
      "Operating income x tax rate (taxes as if Nike had no debt)")
f_row("nopat", "NOPAT (after-tax operating income)", "=B{r[op_income]}-B{r[taxes]}",
      "={c}{r[op_income]}-{c}{r[taxes]}", FMT_USD_M, "Operating income - taxes")
f_row("da", "Plus: depreciation & amortization", f"=Historicals!{hk}{H['da']}", "={c}{r[revenue]}*DA_Pct",
      FMT_USD_M, "Revenue x D&A % (added back: it is an expense but not a cash payment)")
f_row("capex", "Less: capital expenditures", f"=Historicals!{hk}{H['capex']}", "={c}{r[revenue]}*Capex_Pct",
      FMT_USD_M, "Revenue x capex % (cash spent on stores, offices, equipment, software)")
f_row("nwc", "Operating working capital (balance at year end)", f"=Historicals!{hk}{H['nwc']}",
      "={c}{r[revenue]}*NWC_Pct", FMT_USD_M, "Revenue x working capital % (inventory + receivables etc. - payables)")
f_row("delta_nwc", "Less: increase in working capital",
      f"=B{{r[nwc]}}-Historicals!{hp}{H['nwc']}", "={c}{r[nwc]}-{p}{r[nwc]}", FMT_USD_M,
      "This year's working capital - last year's (a decrease frees up cash)")
f_row("fcff", "Free cash flow to the firm (FCFF)",
      "=B{r[nopat]}+B{r[da]}-B{r[capex]}-B{r[delta_nwc]}",
      "={c}{r[nopat]}+{c}{r[da]}-{c}{r[capex]}-{c}{r[delta_nwc]}", FMT_USD_M,
      "NOPAT + D&A - capex - increase in working capital: cash available to all investors", bold=True)
ws_f.append([])
ws_f.append(["Checks and comparisons"]); ws_f.cell(row=ws_f.max_row, column=1).font = BOLD
f_row("fcff_margin", "FCFF margin", "=B{r[fcff]}/B{r[revenue]}", "={c}{r[fcff]}/{c}{r[revenue]}", FMT_PCT,
      "FCFF / revenue")
f_row("reinvest", "Net reinvestment", "=B{r[capex]}-B{r[da]}+B{r[delta_nwc]}",
      "={c}{r[capex]}-{c}{r[da]}+{c}{r[delta_nwc]}", FMT_USD_M,
      "Capex - D&A + increase in working capital (the reverse DCF used change in revenue / 3.2 instead)")
ws_f.append(["Simple FCF reported in FY2026 (operating cash flow - capex)", f"=Historicals!{hk}{H['fcf']}"])
ws_f[f"B{ws_f.max_row}"].font, ws_f[f"B{ws_f.max_row}"].number_format = GREEN, FMT_USD_M
ws_f[f"{NOTE_COL}{ws_f.max_row}"] = ("For comparison with column B's FCFF. They differ because FCFF uses a normalized "
                                    "18% tax on operating income and excludes interest and other income.")
ws_f.column_dimensions["A"].width = 50
for c in range(2, 3 + N_FC):
    ws_f.column_dimensions[get_column_letter(c)].width = 15
ws_f.column_dimensions[NOTE_COL].width = 90
ws_f.freeze_panes = "B5"

# ---------------------------------------------------------------------------
# STEP 8. Valuation tab: discount, terminal value, equity value per share
# ---------------------------------------------------------------------------
ws_v = wb.create_sheet("Valuation")
ws_v["A1"] = "Valuation: from forecast cash flows to value per share"
ws_v["A1"].font = TITLE
ws_v["A2"] = ("Each year's cash flow is worth less the further away it is: divide it by (1 + WACC) "
              "once per year between the valuation date and the end of that fiscal year.")
ws_v.append([])
ws_v.append(["Part 1: present value of FY2027-FY2031 cash flows"] + [f"FY{y}" for y in FC_YEARS] + ["How it is calculated"])
style_header_row(ws_v, 4, 2 + N_FC)
vcol = {y: get_column_letter(2 + i) for i, y in enumerate(FC_YEARS)}
VNOTE = get_column_letter(2 + N_FC)
V = {}


def v_row(key, label, template, fmt, note):
    ws_v.append([label])
    r = ws_v.max_row
    V[key] = r
    for i, y in enumerate(FC_YEARS):
        c = ws_v[f"{vcol[y]}{r}"]
        c.value = template.format(c=vcol[y], y=y, fc=fcol[y], r=V, first=(i == 0))
        c.font = link_font(c.value, "Valuation")
        c.number_format = fmt
    ws_v[f"{VNOTE}{r}"] = note


v_row("fy_end", "Fiscal year end", "=DATE({y},5,31)", FMT_DATE, "Nike's fiscal year ends May 31")
v_row("years", "Years from valuation date", "=({c}{r[fy_end]}-Valuation_Date)/365.25", FMT_NUM4,
      "(Year-end date - valuation date) / 365.25 days")
ws_v.append(["Share of the year's cash flow counted"])
r = ws_v.max_row
V["share"] = r
for i, y in enumerate(FC_YEARS):
    c = ws_v[f"{vcol[y]}{r}"]
    c.value = "=Share_Of_FY2027_Remaining" if i == 0 else 1
    c.font, c.number_format = (GREEN if i == 0 else BLACK), "0%"
ws_v[f"{VNOTE}{r}"] = "FY2027: only Sep-May are still to come (Jun-Aug cash is already in the 10-Q balance sheet)"
v_row("fcff", "FCFF (from Forecast)", "=Forecast!{fc}" + str(F["fcff"]), FMT_USD_M, "Forecast tab, FCFF row")
v_row("fcff_counted", "FCFF counted", "={c}{r[fcff]}*{c}{r[share]}", FMT_USD_M, "FCFF x share counted")
v_row("df", "Discount factor", "=1/(1+WACC)^{c}{r[years]}", FMT_NUM4, "1 / (1 + WACC) ^ years")
v_row("pv", "Present value of FCFF", "={c}{r[fcff_counted]}*{c}{r[df]}", FMT_USD_M, "FCFF counted x discount factor")

LAST_FC = vcol[FC_YEARS[-1]]
FIRST_FC = vcol[FC_YEARS[0]]
ws_v.append([])
ws_v.append(["Part 2: from enterprise value to value per share", "Value", "How it is calculated"])
style_header_row(ws_v, ws_v.max_row, 3)


def v_line(name, label, formula, fmt, note, key=False):
    ws_v.append([label, formula, note])
    r = ws_v.max_row
    c = ws_v.cell(row=r, column=2)
    c.number_format = fmt
    c.font = link_font(formula, "Valuation")
    if key:
        for cc in (1, 2):
            ws_v.cell(row=r, column=cc).fill = KEY_FILL
            ws_v.cell(row=r, column=cc).font = BOLD
    if name:
        add_name(wb, name, "Valuation", (2, r))
    return r


v_line("Sum_PV_FCFF", "Sum of present values, FY2027-FY2031 (USD m)",
       f"=SUM({FIRST_FC}{V['pv']}:{LAST_FC}{V['pv']})", FMT_USD_M, "Add up Part 1's last row")
v_line(None, "WACC", "=WACC", FMT_PCT2, "From the WACC tab")
v_line(None, "Terminal growth", "=Terminal_Growth", FMT_PCT, "From Assumptions")
# FY2032 is built as a normal year growing at the terminal rate, line by line, rather than
# FY2031 FCFF x (1 + g): FY2031's FCFF includes working capital for FY2031's own growth
# rate, which should not be repeated forever (same method as scripts/dcf_model.py).
FC_LAST = fcol[FC_YEARS[-1]]
v_line("Revenue_FY2032", "FY2032 revenue (USD m)", f"=Forecast!{FC_LAST}{F['revenue']}*(1+Terminal_Growth)",
       FMT_USD_M, "FY2031 revenue x (1 + terminal growth)")
v_line("FCFF_FY2032", "FY2032 FCFF (first year after the forecast) (USD m)",
       f"=Revenue_FY2032*(Forecast!{FC_LAST}{F['margin']}*(1-Tax_Rate)+DA_Pct-Capex_Pct)"
       f"-NWC_Pct*(Revenue_FY2032-Forecast!{FC_LAST}{F['revenue']})", FMT_USD_M,
       "FY2032 revenue x (FY2031 margin x (1 - tax) + D&A % - capex %) - working capital % x revenue increase: "
       "a steady year growing at the terminal rate")
v_line("Terminal_Value", "Terminal value at end of FY2031 (USD m)", "=FCFF_FY2032/(WACC-Terminal_Growth)", FMT_USD_M,
       "FY2032 FCFF / (WACC - terminal growth): value of all cash flows after FY2031 (growing-perpetuity formula)")
v_line("PV_Terminal_Value", "Present value of terminal value (USD m)", f"=Terminal_Value*{LAST_FC}{V['df']}", FMT_USD_M,
       "Terminal value x FY2031 discount factor")
v_line("Enterprise_Value", "Enterprise value (USD m)", "=Sum_PV_FCFF+PV_Terminal_Value", FMT_USD_M,
       "Value of the business to all investors (debt + equity)")
v_line(None, "Plus: cash and short-term investments (USD m)", "=Cash+ST_Investments", FMT_USD_M,
       "From Assumptions (10-Q, 2026-08-31)")
v_line(None, "Less: debt, excl. leases (USD m)", "=Total_Debt", FMT_USD_M, "From the WACC tab")
v_line("Equity_Value", "Equity value (USD m)", f"=Enterprise_Value+B{ws_v.max_row - 1}-B{ws_v.max_row}", FMT_USD_M,
       "Enterprise value + cash - debt: what belongs to shareholders")
v_line(None, "Diluted shares (millions)", "=Shares", "#,##0.0", "From Assumptions")
v_line("Value_Per_Share", "Value per share (USD)", "=Equity_Value/Shares", FMT_USD, "Equity value / shares", key=True)
v_line(None, "Share price on valuation date (USD)", "=Share_Price", FMT_USD, "From Assumptions")
v_line("Upside", "Value vs price", "=Value_Per_Share/Share_Price-1", FMT_PCT,
       "Positive = the model says the shares are worth more than the price", key=True)
v_line(None, "Terminal value as % of enterprise value", "=PV_Terminal_Value/Enterprise_Value", FMT_PCT,
       "How much of the value comes from after FY2031 (high = more depends on the long run)")
v_line(None, "Implied EV / FY2026 operating income", f"=Enterprise_Value/Forecast!B{F['op_income']}", "0.0x",
       "A sanity check multiple")

# Sensitivity table: value per share for different WACC (columns) and terminal growth (rows).
# Each cell redoes the valuation with its own WACC and growth using the same FCFF row, so it
# stays a live formula (no Excel "data table" needed).
ws_v.append([])
ws_v.append(["Part 3: value per share (USD) for other discount rates and terminal growth rates"])
ws_v.cell(row=ws_v.max_row, column=1).font = BOLD
ws_v.append(["Terminal growth (down) / WACC (across)"])
hdr = ws_v.max_row
steps = [-2, -1, 0, 1, 2]
for j, s in enumerate(steps):
    c = ws_v.cell(row=hdr, column=2 + j, value=f"=WACC+({s})*Sens_WACC_Step")
    c.number_format, c.font, c.fill = FMT_PCT, BOLD, HEADER_FILL
ws_v.cell(row=hdr, column=1).fill = HEADER_FILL
ws_v.cell(row=hdr, column=1).font = BOLD
sens_first_row = hdr + 1
pv_range = lambda w: (f"SUMPRODUCT(${FIRST_FC}${V['fcff_counted']}:${LAST_FC}${V['fcff_counted']},"
                      f"1/(1+{w})^${FIRST_FC}${V['years']}:${LAST_FC}${V['years']})")
for i, s in enumerate(steps):
    r = sens_first_row + i
    g = ws_v.cell(row=r, column=1, value=f"=Terminal_Growth+({s})*Sens_Growth_Step")
    g.number_format, g.font, g.fill = FMT_PCT, BOLD, HEADER_FILL
    for j in range(len(steps)):
        w = f"{get_column_letter(2 + j)}${hdr}"
        gg = f"$A{r}"
        formula = (f"=({pv_range(w)}+(Forecast!${FC_LAST}${F['revenue']}*(1+{gg})*(Forecast!${FC_LAST}${F['margin']}*(1-Tax_Rate)+DA_Pct-Capex_Pct)-NWC_Pct*Forecast!${FC_LAST}${F['revenue']}*{gg})/({w}-{gg})/(1+{w})^${LAST_FC}${V['years']}"
                   f"+Cash+ST_Investments-Total_Debt)/Shares")
        c = ws_v.cell(row=r, column=2 + j, value=formula)
        c.number_format = FMT_USD
        if s == 0 and steps[j] == 0:
            c.fill, c.font = KEY_FILL, BOLD
ws_v.cell(row=sens_first_row + len(steps), column=1,
          value="The centre cell equals the value per share above. Each cell repeats Part 1 and Part 2 with that "
                "row's growth and that column's WACC.")

ws_v.append([])
ws_v.append(["Part 4: comparison with the reverse DCF (output/04_reverse_dcf_results.md)"])
ws_v.cell(row=ws_v.max_row, column=1).font = BOLD
for line in [
    "The reverse DCFs (scripts 04 and 06) run this same model backwards: they fix the value at the share price "
    "and solve for the growth and margin it implies (output/06_implied_growth_and_margin_results.md).",
    "To do the same here, use Excel's Goal Seek: Data > What-If Analysis > Goal Seek, set cell 'Value_Per_Share' "
    "to the share price by changing 'Growth_Adjustment' on Assumptions.",
    "Python copy of this model: scripts/dcf_model.py. Script 06 checks the two give the same value to the cent.",
]:
    ws_v.append([line])
ws_v.column_dimensions["A"].width = 58
for c in range(2, 2 + N_FC):
    ws_v.column_dimensions[get_column_letter(c)].width = 14
ws_v.column_dimensions[VNOTE].width = 85

# ---------------------------------------------------------------------------
# STEP 9. README tab
# ---------------------------------------------------------------------------
readme = [
    ("Nike (NKE) 5-year DCF model", TITLE),
    (f"Built {date.today().isoformat()} by scripts/05_excel_dcf_model.py. Valuation date {A.VALUATION_DATE['value']}. "
     "All money in USD millions unless labelled. Fiscal year ends May 31.", None),
    ("", None),
    ("How the tabs connect (money flows left to right)", BOLD),
    ("1. Assumptions: every input. Change a yellow cell and everything else updates.", None),
    ("2. Historicals: Nike's FY2017-FY2026 10-K figures and ratios. Use its averages to judge the assumptions.", None),
    ("3. Sources: the SEC filing (accession number) behind each historical figure.", None),
    ("4. WACC: builds the discount rate from the market inputs on Assumptions.", None),
    ("5. Forecast: starts from FY2026 actual revenue (Historicals), sets FY2027 from Nike's guidance (revenue -8%, "
     "margin 5.55%), and applies the Assumptions to get FY2027-FY2031 free cash flow (FCFF).", None),
    ("6. Valuation: discounts the Forecast's FCFF at the WACC, adds a terminal value for the years after FY2031, "
     "adds cash, subtracts debt, divides by shares, and compares with the share price.", None),
    ("", None),
    ("Colour code", BOLD),
    ("Blue on yellow = an input you can change (Assumptions tab).", BLUE),
    ("Blue = a historical number typed in from SEC filings.", BLUE),
    ("Black = a formula on the same tab.", BLACK),
    ("Green = a formula that uses a number from another tab.", GREEN),
    ("", None),
    ("Formulas use names for inputs (e.g. =Revenue*(1+Growth_FY2027), =1/(1+WACC)^years). "
     "Formulas > Name Manager lists every name and the cell it points to.", None),
    ("", None),
    ("Weak spots", BOLD),
    ("Equity risk premium 4.09% is Damodaran's 1 September 2026 figure, verified against his data file (data/raw/damodaran/). "
     "It was 4.23% at the start of 2026.", None),
    ("Shares are the quarter's diluted weighted average, not the exact count on 2026-08-31.", None),
    ("Leases are left out of debt and of operating income consistently (lease cost sits inside S&A).", None),
    ("The terminal value builds FY2032 as a normal year growing 2.5% (working capital grows with that 2.5%), "
     "so FY2031's own growth-driven working-capital spending is not repeated forever.", None),
]
for text, font in readme:
    ws_readme.append([text])
    if font is not None:
        ws_readme.cell(row=ws_readme.max_row, column=1).font = font
ws_readme.column_dimensions["A"].width = 130

# ---------------------------------------------------------------------------
# STEP 10. Save, recalculate in LibreOffice, check for errors, export CSVs
# ---------------------------------------------------------------------------
OUT_XLSX.parent.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    raw_path = Path(tmp) / "model.xlsx"
    wb.save(raw_path)
    # openpyxl writes formulas but cannot compute them. LibreOffice opens the file,
    # computes every formula, and saves a copy that also stores the results.
    out_dir = Path(tmp) / "recalc"
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out_dir), str(raw_path)],
                   check=True, capture_output=True, timeout=180)
    shutil.copy(out_dir / "model.xlsx", OUT_XLSX)

values = load_workbook(OUT_XLSX, data_only=True)     # computed values
formulas = load_workbook(OUT_XLSX)                    # formulas
errors, n_formulas = [], 0
for ws in formulas.worksheets:
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                n_formulas += 1
                v = values[ws.title][cell.coordinate].value
                if v is None or (isinstance(v, str) and v.startswith(("#", "Err"))):
                    errors.append(f"{ws.title}!{cell.coordinate} {cell.value} -> {v}")
print(f"{n_formulas} formulas checked, {len(errors)} errors")
for e in errors[:20]:
    print("  ", e)


def sheet_table(ws_name, first_row, n_cols):
    """Read a computed table (label + values) from the recalculated workbook."""
    ws = values[ws_name]
    rows = []
    for r in ws.iter_rows(min_row=first_row, max_col=n_cols, values_only=True):
        if r[0] is None:
            continue
        rows.append(list(r))
    return rows


fc_rows = sheet_table("Forecast", 5, 2 + N_FC)
pd.DataFrame(fc_rows, columns=["Line (USD m unless % )", f"FY{BASE_FY} actual"] + [f"FY{y} forecast" for y in FC_YEARS]) \
    .to_csv(OUT_FORECAST_CSV, index=False)
val_rows = sheet_table("Valuation", 5, 1 + N_FC)
pd.DataFrame(val_rows, columns=["Item"] + [f"col{i}" for i in range(1, 1 + N_FC)]).to_csv(OUT_VALUATION_CSV, index=False)
sens = [[values["Valuation"].cell(row=r, column=c).value for c in range(1, 2 + len(steps))]
        for r in range(hdr, hdr + 1 + len(steps))]
sens_df = pd.DataFrame([row[1:] for row in sens[1:]], index=[f"g={row[0]:.1%}" for row in sens[1:]],
                       columns=[f"WACC={w:.2%}" for w in sens[0][1:]])
sens_df.round(2).to_csv(OUT_SENS_CSV)

vps = values["Valuation"][f"B{[r for r in range(1, values['Valuation'].max_row + 1) if values['Valuation'].cell(row=r, column=1).value == 'Value per share (USD)'][0]}"].value
print(f"Value per share: ${vps:.2f} vs price ${A.SHARE_PRICE['value']:.2f}")
print(f"Saved {OUT_XLSX.relative_to(ROOT)}, {OUT_FORECAST_CSV.name}, {OUT_VALUATION_CSV.name}, {OUT_SENS_CSV.name}")
if errors:
    raise SystemExit("Formula errors found; see above.")
