"""
08_peer_multiples.py  -  Nike next to five competitors on EV/EBITDA, P/E, growth and margin

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
Scripts 04-06 ask what Nike's share price implies. This script asks a simpler,
market-wide question: per dollar of profit, is Nike priced higher or lower than
adidas, Lululemon, Deckers, On Holding and Under Armour? And how do their growth
and margins compare?

For each company it builds four numbers:
  EV/EBITDA        enterprise value / EBITDA (earnings before interest, tax,
                   depreciation and amortization), both over the last twelve months
  P/E              market value of the shares / net income, last twelve months
  Revenue growth   (a) last twelve months vs the twelve months a year earlier
                   (b) compound annual growth over the last 3 fiscal years
  Operating margin operating income / revenue, last twelve months, as reported

Key terms
  Last twelve months (TTM): the latest full fiscal year, plus the part of the new
      year reported so far, minus the same part of the year before.
      Example (Nike): FY2026 (Jun 2025-May 2026) + Q1 FY2027 (Jun-Aug 2026)
      - Q1 FY2026 (Jun-Aug 2025) = Sep 2025 to Aug 2026.
  Enterprise value (EV): what it would cost to buy the whole business: market value
      of shares + debt - cash. Leases are left out for every company, the same as
      in Nike's DCF (output/04_latest_balance_sheet_and_shares.csv).
  Market value of shares: share price on 2026-10-02 x diluted weighted-average
      shares of the latest quarter (the share count Nike's model uses).

Where the numbers come from (project rule 2: SEC first)
  Nike, Lululemon, Deckers, Under Armour  SEC 10-K / 10-Q, XBRL company facts files
  On Holding (CHF, IFRS)                  SEC 20-F (company facts) + the 6-K half-year
                                          reports for 2025 and 2026 (XBRL instance files)
  adidas (EUR, IFRS)                      NOT an SEC filer. Annual Report 2025 pages from
                                          report.adidas-group.com, saved in data/raw/competitors/.
                                          adidas's 2026 half-year report sits on
                                          plus the 2025 and 2026 Half Year Reports (PDFs from
                                          res.cloudinary.com, linked from www.adidas-group.com).
  Prices and exchange rates               Yahoo on 2026-10-02, typed into assumptions.py and
                                          checked against data/raw/peer_prices_fx_yfinance_2026-10-02.csv

Two fairness adjustments (both in assumptions.py)
  1. Currencies. On reports in Swiss francs but its shares trade in US dollars, so its
     figures are converted to USD at the 2026-10-02 rate before dividing. adidas reports
     and trades in euros, so its ratios need no conversion. USD sizes are shown for all.
  2. Leases. Under IFRS (adidas, On) rent is not an operating cost: it is split into
     right-of-use depreciation (inside D&A) and lease interest (below operating profit).
     Adding back all D&A would then add back rent, flattering their EBITDA versus the
     US GAAP companies. So IFRS EBITDA = operating profit + D&A - right-of-use
     depreciation - lease interest. Operating margin stays as reported (the 06b basis).

Outputs
  output/08_peer_inputs.csv          every number pulled, with period, form, accession, filed date
  output/08_peer_multiples.csv       the comparison table, every intermediate step as a column
  output/08_peer_multiples.xlsx      the same table with live Excel formulas, plus inputs, checks and notes
  output/08_peer_checks.csv          factors the table leaves out, each switched on alone (leases as debt,
                                     average FX for On, Under Armour before restructuring, adidas variants)
  output/08_nike_value_from_peers.csv  Nike's value per share at peer multiples, next to the DCF and the price
Run after 06b (it reads adidas's 2022 sales from output/06b_competitors_by_year.csv).
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assumptions as A  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
COMP = RAW / "competitors"
OUT = ROOT / "output"

PRICE_DATE = A.VALUATION_DATE["value"]                                     # 2026-10-02
PRICES = dict(A.PEER_SHARE_PRICES["value"], Nike=A.SHARE_PRICE["value"])   # per share, trading currency
FX = A.FX_RATES_TO_USD["value"]                                            # USD per unit of currency
CAGR_YEARS = A.PEER_GROWTH_CAGR_YEARS["value"]
LEASE_ADJ = A.PEER_IFRS_LEASE_ADJUSTMENT["value"]
TOL = pd.Timedelta(days=10)       # 52/53-week fiscal years end a few days apart from year to year

inputs = []                       # every number this script uses, for output/08_peer_inputs.csv


def note_input(company, item, value, currency, period, source):
    inputs.append({"company": company, "item": item, "value": value, "currency": currency,
                   "period": period, "source": source})
    return value


# ---------------------------------------------------------------------------
# STEP 0. Check the prices and FX rates typed into assumptions.py against the raw download
# ---------------------------------------------------------------------------
raw_px = pd.read_csv(RAW / "peer_prices_fx_yfinance_2026-10-02.csv")
raw_px = raw_px[raw_px["date"] == PRICE_DATE].set_index("ticker")["close"]
TICKERS = {"Nike": "NKE", "Lululemon": "LULU", "Deckers": "DECK", "On Holding": "ONON",
           "Under Armour": "UAA", "adidas": "ADS.DE"}
for name, tk in TICKERS.items():
    assert abs(raw_px[tk] - PRICES[name]) < 0.006, f"{name} price in assumptions.py differs from Yahoo file"
for cur, tk in {"EUR": "EURUSD=X", "CHF": "CHFUSD=X"}.items():
    assert abs(raw_px[tk] - FX[cur]) < 0.0001, f"{cur} rate in assumptions.py differs from Yahoo file"


# ---------------------------------------------------------------------------
# STEP 1. Read SEC XBRL facts into one simple list per tag
# ---------------------------------------------------------------------------
# Each fact: start date (None for balance-sheet items), end date, value, form,
# accession number, filed date. Only periodic reports are used.
FORMS = ("10-K", "10-Q", "20-F", "6-K")


def load_companyfacts(path, ns):
    """Company facts JSON from data.sec.gov -> {tag: [fact, ...]} (whole-company values only)."""
    facts = json.loads(path.read_text())["facts"][ns]
    out = {}
    for tag, body in facts.items():
        for unit, xs in body["units"].items():
            for x in xs:
                if x.get("form") in FORMS:
                    out.setdefault(tag, []).append({"start": x.get("start"), "end": x["end"], "val": x["val"],
                                                    "unit": unit, "form": x["form"], "accn": x["accn"],
                                                    "filed": x["filed"]})
    return out


def load_xbrl_instance(path, accn, filed, form="6-K"):
    """An XBRL instance file (as filed with a 6-K) -> (whole-company facts, facts split by share class).
    Contexts say which period a number covers and whether it is for one share class only."""
    t = path.read_text(encoding="utf-8")
    ctx = {}
    for m in re.finditer(r'<(?:xbrli:)?context id="([^"]+)">(.*?)</(?:xbrli:)?context>', t, re.S):
        body = m.group(2)
        start = re.search(r"startDate>([^<]+)", body)
        end = re.search(r"(?:endDate|instant)>([^<]+)", body)
        members = tuple(x.strip() for x in re.findall(r"<(?:xbrldi:)?explicitMember[^>]*>([^<]+)<", body))
        ctx[m.group(1)] = (start.group(1) if start else None, end.group(1), members)
    whole, by_class = {}, {}
    for m in re.finditer(r'<ifrs-full:(\w+)\s([^>]*contextRef="([^"]+)"[^>]*)>([-\d.]+)<', t):
        tag, _, c, v = m.groups()
        start, end, members = ctx[c]
        fact = {"start": start, "end": end, "val": float(v), "unit": "", "form": form, "accn": accn, "filed": filed}
        if not members:
            whole.setdefault(tag, []).append(fact)
        elif len(members) == 1:
            by_class.setdefault((tag, members[0]), []).append(fact)
    return whole, by_class


def days(f):
    return (pd.Timestamp(f["end"]) - pd.Timestamp(f["start"])).days


def periods(facts, tags):
    """Duration facts for the first tag (in preference order) that has each period; latest filing wins."""
    out = {}
    for tag in tags:
        for f in facts.get(tag, []):
            if f["start"] is None:
                continue
            key = (f["start"], f["end"])
            if key in out and out[key]["tag"] != tag:
                continue                       # a preferred tag already covers this period
            if key not in out or f["filed"] > out[key]["filed"]:
                out[key] = dict(f, tag=tag)
    return list(out.values())


def near(a, b):
    return abs(pd.Timestamp(a) - pd.Timestamp(b)) <= TOL


def pick(ps, end, length_days=None, annual=False):
    """The period ending near `end`, either a full year or of roughly `length_days`."""
    for f in ps:
        if not near(f["end"], end):
            continue
        if annual and 350 <= days(f) <= 380:
            return f
        if length_days is not None and abs(days(f) - length_days) <= 10:
            return f
    raise LookupError(f"no period ending near {end}")


def ttm(facts, tags, latest_end):
    """Last-twelve-month value ending at latest_end, and the same twelve months a year earlier.
    TTM = latest full year + year-to-date - same year-to-date a year before."""
    ps = periods(facts, tags)
    one_year = pd.DateOffset(years=1)
    try:                                       # the latest report is itself a full year
        a = pick(ps, latest_end, annual=True)
        a_prev = pick(ps, pd.Timestamp(latest_end) - one_year, annual=True)
        return a["val"], a_prev["val"], [a, a_prev]
    except LookupError:
        pass
    ytd = max((f for f in ps if f["end"] == latest_end and days(f) < 350), key=days)
    a = pick(ps, pd.Timestamp(ytd["start"]) - pd.Timedelta(days=1), annual=True)
    a_prev = pick(ps, pd.Timestamp(a["end"]) - one_year, annual=True)
    ytd_prev = pick(ps, pd.Timestamp(latest_end) - one_year, length_days=days(ytd))
    ytd_prev2 = pick(ps, pd.Timestamp(latest_end) - 2 * one_year, length_days=days(ytd))
    now = a["val"] + ytd["val"] - ytd_prev["val"]
    year_ago = a_prev["val"] + ytd_prev["val"] - ytd_prev2["val"]
    return now, year_ago, [a, ytd, ytd_prev, a_prev, ytd_prev2]


def describe(parts):
    return "; ".join(f"{p['tag']} {p['start']}..{p['end']} = {p['val']/1e6:,.1f}m ({p['form']} {p['accn']} filed {p['filed']})"
                     for p in parts)


def instant(facts, tags, end):
    """Balance-sheet value(s) at `end`, summed over tags; a tag with no value at that date counts as 0."""
    total, used = 0.0, []
    for tag in tags:
        hits = [f for f in facts.get(tag, []) if f["start"] is None and f["end"] == end]
        if hits:
            f = max(hits, key=lambda x: x["filed"])
            total += f["val"]
            used.append(f"{tag} = {f['val']/1e6:,.1f}m ({f['form']} {f['accn']} filed {f['filed']})")
        else:
            used.append(f"{tag}: no value at {end}, counted as 0")
    return total, "; ".join(used)


def latest_quarter_shares(facts, tag, end):
    """Diluted weighted-average shares for the latest quarter (about 91 days) ending at `end`."""
    ps = [f for f in periods(facts, [tag]) if f["end"] == end]
    f = min(ps, key=days)
    return f["val"], describe([f])


def annual_revenue(facts, tags):
    """Every full fiscal year of revenue: {end date: fact}."""
    return {f["end"]: f for f in periods(facts, tags) if 350 <= days(f) <= 380}


def cagr_from_annuals(annuals, latest_fy_end):
    """Compound annual growth from the fiscal year ending ~CAGR_YEARS before the latest one.
    If no year ends exactly there (52/53-week years), use the closest year end and the
    actual number of years between the two."""
    target = pd.Timestamp(latest_fy_end) - pd.DateOffset(years=CAGR_YEARS)
    base_end = min(annuals, key=lambda e: abs(pd.Timestamp(e) - target))
    yrs = (pd.Timestamp(latest_fy_end) - pd.Timestamp(base_end)).days / 365.25
    first, last = annuals[base_end]["val"], annuals[latest_fy_end]["val"]
    return ((last / first) ** (1 / yrs) - 1) * 100, base_end, yrs, first, last


# ---------------------------------------------------------------------------
# STEP 2. Which tags to read for each SEC company
# ---------------------------------------------------------------------------
# Each item lists XBRL tags in order of preference. "op_income" for Nike is built
# from gross profit and S&A (Nike has no operating income line; project definition).
US_GAAP = {
    "Nike": {
        "file": RAW / "companyfacts_CIK0000320187_2026-10-04.json", "latest_end": "2026-08-31",
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "gross_profit": ["GrossProfit"], "sga": ["SellingGeneralAndAdministrativeExpense"],
        "da": ["DepreciationDepletionAndAmortization", "Depreciation"],
        "net_income": ["NetIncomeLoss"],
    },
    "Lululemon": {
        "file": COMP / "companyfacts_CIK0001397187_lululemon_2026-10-04.json", "latest_end": "2026-08-02",
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax"], "op_income": ["OperatingIncomeLoss"],
        "da": ["DepreciationDepletionAndAmortization", "Depreciation"], "net_income": ["NetIncomeLoss"],
        "cash": ["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
        "debt": ["ShortTermBorrowings", "OtherBorrowings"],
        "shares": "WeightedAverageNumberOfDilutedSharesOutstanding",
    },
    "Deckers": {
        "file": COMP / "companyfacts_CIK0000910521_deckers_2026-10-04.json", "latest_end": "2026-06-30",
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax"], "op_income": ["OperatingIncomeLoss"],
        "da": ["DepreciationAmortizationAndAccretionNet", "DepreciationDepletionAndAmortization"],
        "net_income": ["NetIncomeLoss"],
        "cash": ["CashAndCashEquivalentsAtCarryingValue"], "debt": ["ShortTermBorrowings", "LongTermDebt"],
        "shares": "WeightedAverageNumberOfDilutedSharesOutstanding",
    },
    "Under Armour": {
        "file": COMP / "companyfacts_CIK0001336917_under_armour_2026-10-04.json", "latest_end": "2026-06-30",
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "op_income": ["OperatingIncomeLoss"],
        "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
        "net_income": ["NetIncomeLoss"],
        "cash": ["CashAndCashEquivalentsAtCarryingValue"], "debt": ["LongTermDebtNoncurrent", "LongTermDebtCurrent"],
        "shares": "WeightedAverageNumberOfDilutedSharesOutstanding",
    },
}

results = {}

for name, cfg in US_GAAP.items():
    facts = load_companyfacts(cfg["file"], "us-gaap")
    E = cfg["latest_end"]
    r = {"company": name, "report_currency": "USD", "price_currency": "USD", "gaap": "US GAAP",
         "latest_period_end": E, "basis": "TTM (last full fiscal year + year to date - prior year to date)"}

    rev, rev_prev, parts = ttm(facts, cfg["revenue"], E)
    note_input(name, "Revenue TTM", rev / 1e6, "USD", E, describe(parts))
    note_input(name, "Revenue TTM one year earlier", rev_prev / 1e6, "USD", "", "same filings as above")
    if name == "Nike":       # operating income = gross profit - S&A (project definition)
        gp, _, p1 = ttm(facts, cfg["gross_profit"], E)
        sga, _, p2 = ttm(facts, cfg["sga"], E)
        oi = gp - sga
        note_input(name, "Gross profit TTM", gp / 1e6, "USD", E, describe(p1[:3]))
        note_input(name, "Selling & administrative expense TTM", sga / 1e6, "USD", E, describe(p2[:3]))
        note_input(name, "Operating income TTM (gross profit - S&A)", oi / 1e6, "USD", E, "calculated")
    else:
        oi, _, p = ttm(facts, cfg["op_income"], E)
        note_input(name, "Operating income TTM", oi / 1e6, "USD", E, describe(p[:3]))
    da, _, p = ttm(facts, cfg["da"], E)
    note_input(name, "Depreciation & amortization TTM", da / 1e6, "USD", E, describe(p[:3]))
    ni, _, p = ttm(facts, cfg["net_income"], E)
    note_input(name, "Net income TTM", ni / 1e6, "USD", E, describe(p[:3]))

    annuals = annual_revenue(facts, cfg["revenue"])
    fy_end = max(e for e in annuals if e <= E)
    g3, base_end, yrs, first, last = cagr_from_annuals(annuals, fy_end)
    note_input(name, "Revenue, latest fiscal year", last / 1e6, "USD", fy_end, describe([annuals[fy_end]]))
    note_input(name, "Revenue, fiscal year at start of CAGR window", first / 1e6, "USD", base_end,
               describe([annuals[base_end]]) + f"; window {yrs:.2f} years")

    if name == "Nike":       # reuse the exact balance sheet and share count of Nike's DCF
        bs = pd.read_csv(OUT / "04_latest_balance_sheet_and_shares.csv").set_index("item")["value"]
        debt, cash = bs["Total debt, excl. leases (USD m)"] * 1e6, bs["Cash + short-term investments (USD m)"] * 1e6
        shares = bs["Diluted weighted-average shares, latest quarter (millions)"] * 1e6
        src = "output/04_latest_balance_sheet_and_shares.csv (Nike 10-Q filed 2026-10-02)"
        debt_src = cash_src = shares_src = src
    else:
        debt, debt_src = instant(facts, cfg["debt"], E)
        cash, cash_src = instant(facts, cfg["cash"], E)
        shares, shares_src = latest_quarter_shares(facts, cfg["shares"], E)
    note_input(name, "Debt excl. leases", debt / 1e6, "USD", E, debt_src)
    note_input(name, "Cash (and short-term investments)", cash / 1e6, "USD", E, cash_src)
    note_input(name, "Diluted weighted-average shares, latest quarter (m)", shares / 1e6, "shares", E, shares_src)

    # For the checks in step 5b: lease liabilities, fixed lease cost of the latest fiscal year
    # (not split by quarter for most companies, so the full-year figure stands in for TTM), and
    # restructuring charges where a company tags them.
    lease_liab, lease_src = instant(facts, ["OperatingLeaseLiabilityCurrent", "OperatingLeaseLiabilityNoncurrent"], E)
    note_input(name, "Operating lease liabilities (check only)", lease_liab / 1e6, "USD", E, lease_src)
    lc = [f for f in periods(facts, ["OperatingLeaseCost"]) if f["end"] == fy_end and 350 <= days(f) <= 380][0]
    note_input(name, "Operating lease cost, latest fiscal year (check only)", lc["val"] / 1e6, "USD", fy_end, describe([lc]))
    restructuring = 0.0
    if "RestructuringCostsAndAssetImpairmentCharges" in facts and name == "Under Armour":
        restructuring, _, p = ttm(facts, ["RestructuringCostsAndAssetImpairmentCharges"], E)
        note_input(name, "Restructuring and impairment charges TTM (check only)", restructuring / 1e6, "USD", E, describe(p[:3]))

    r.update(revenue=rev, revenue_year_ago=rev_prev, op_income=oi, da=da, rou_depreciation=0.0, lease_interest=0.0,
             lease_liab=lease_liab, fixed_lease_cost=lc["val"], restructuring=restructuring, nci=0.0,
             net_income=ni, debt=debt, cash=cash, shares=shares, cagr=g3,
             cagr_window=f"FY ending {base_end} to FY ending {fy_end} ({yrs:.2f} yrs)")
    results[name] = r

# ---------------------------------------------------------------------------
# STEP 3. On Holding: 20-F (company facts) + 6-K half-year XBRL instances, CHF, IFRS
# ---------------------------------------------------------------------------
name, E = "On Holding", "2026-06-30"
facts = load_companyfacts(COMP / "companyfacts_CIK0001858985_on_holding_2026-10-04.json", "ifrs-full")
h1_26, cls_26 = load_xbrl_instance(COMP / "on_holding_6K_H1_2026_xbrl_instance_onholdingag-20260630_htm_2026-10-04.xml",
                                   "0001858985-26-000018", "2026-08-11")
h1_25, _ = load_xbrl_instance(COMP / "on_holding_6K_H1_2025_xbrl_instance_onholdingag-20250630_htm_2026-10-04.xml",
                              "0001858985-25-000012", "2025-08-12")
for extra in (h1_25, h1_26):              # add the half-year facts to the annual ones
    for tag, xs in extra.items():
        facts.setdefault(tag, []).extend(xs)

r = {"company": name, "report_currency": "CHF", "price_currency": "USD", "gaap": "IFRS", "latest_period_end": E,
     "basis": "TTM (FY2025 20-F + H1 2026 6-K - H1 2025)"}
items = {"revenue": ["RevenueFromContractsWithCustomers"], "op_income": ["ProfitLossFromOperatingActivities"],
         "da": ["AdjustmentsForDepreciationAndAmortisationExpense"], "rou_depreciation": ["DepreciationRightofuseAssets"],
         "lease_interest": ["InterestExpenseOnLeaseLiabilities"], "net_income": ["ProfitLossAttributableToOwnersOfParent"]}
labels = {"revenue": "Revenue TTM", "op_income": "Operating result TTM", "da": "Depreciation & amortization TTM",
          "rou_depreciation": "Right-of-use (lease) depreciation TTM", "lease_interest": "Interest on lease liabilities TTM",
          "net_income": "Net income attributable to shareholders TTM"}
for key, tags in items.items():
    v, v_prev, parts = ttm(facts, tags, E)
    r[key] = v
    note_input(name, labels[key], v / 1e6, "CHF", E, describe(parts[:3]))
    if key == "revenue":
        r["revenue_year_ago"] = v_prev
        note_input(name, "Revenue TTM one year earlier", v_prev / 1e6, "CHF", "", describe(parts[3:]))
annuals = annual_revenue(facts, items["revenue"])
fy_end = max(e for e in annuals if e <= E)
g3, base_end, yrs, first, last = cagr_from_annuals(annuals, fy_end)
note_input(name, "Revenue, latest fiscal year", last / 1e6, "CHF", fy_end, describe([annuals[fy_end]]))
note_input(name, "Revenue, fiscal year at start of CAGR window", first / 1e6, "CHF", base_end, describe([annuals[base_end]]))
cash, cash_src = instant(facts, ["CashAndCashEquivalents"], E)
note_input(name, "Cash", cash / 1e6, "CHF", E, cash_src)
note_input(name, "Debt excl. leases", 0.0, "CHF", E,
           "6-K H1 2026 tags Borrowings = 0 (no bank loans or bonds); lease liabilities excluded")
# On has two share classes. A class B share carries 1/10 of a class A share's economic
# rights (the 6-K shows 10 B shares converting into 1 A share), so B counts as 1/10 of an A.
q = ("2026-04-01", E)
sh_a = [f for f in cls_26[("AdjustedWeightedAverageShares", "onholdingag:ClassASharesMember")] if (f["start"], f["end"]) == q][0]["val"]
sh_b = [f for f in cls_26[("AdjustedWeightedAverageShares", "onholdingag:ClassBVotingSharesMember")] if (f["start"], f["end"]) == q][0]["val"]
shares = sh_a + sh_b / 10
note_input(name, "Diluted weighted-average class A shares, Q2 2026 (m)", sh_a / 1e6, "shares", "2026-04-01..2026-06-30",
           "ifrs-full:AdjustedWeightedAverageShares, class A (6-K 0001858985-26-000018 filed 2026-08-11)")
note_input(name, "Diluted weighted-average class B shares, Q2 2026 (m)", sh_b / 1e6, "shares", "2026-04-01..2026-06-30",
           "same, class B voting shares; each = 1/10 of a class A share economically")
note_input(name, "Diluted shares, class A equivalents (m)", shares / 1e6, "shares", E, "class A + class B / 10")
lease_liab, lease_src = instant(facts, ["CurrentLeaseLiabilities", "NoncurrentLeaseLiabilities"], E)
note_input(name, "Lease liabilities (check only)", lease_liab / 1e6, "CHF", E, lease_src)
note_input(name, "Non-controlling interests", 0.0, "CHF", E, "none reported in the 6-K H1 2026 balance sheet")
r.update(debt=0.0, cash=cash, shares=shares, nci=0.0, lease_liab=lease_liab, restructuring=0.0,
         fixed_lease_cost=r["rou_depreciation"] + r["lease_interest"],
         cagr=g3, cagr_window=f"FY ending {base_end} to FY ending {fy_end} ({yrs:.2f} yrs)")
results[name] = r

# ---------------------------------------------------------------------------
# STEP 4. adidas: Annual Report 2025 (NON-SEC), EUR, IFRS, calendar 2025
# ---------------------------------------------------------------------------
name = "adidas"
AR = "https://report.adidas-group.com/2025/en/consolidated-financial-statements"


def adidas_table(fname, row_label, col=0, table=0):
    """One number from a saved adidas report page. `col` 0 = 2025, 1 = 2024.
    The pages put the label in the first cell; numbers use ',' for thousands and (x) for negatives."""
    t = pd.read_html(COMP / fname, thousands=None)[table].map(str)
    t.columns = range(t.shape[1])
    row = t[t[0].str.strip().str.startswith(row_label)].iloc[0]
    nums = [v for v in row.values[1:] if re.fullmatch(r"\(?[\d,]+(\.\d+)?\)?", v.strip())]
    nums = [v for v in nums if not re.fullmatch(r"\d{2}", v.strip())]    # drop note references like '36'
    v = nums[col].strip()
    neg = v.startswith("(")
    v = float(v.strip("()").replace(",", ""))
    return -v if neg else v


def ad(item, fname, label, page, col=0, table=0):
    v = adidas_table(fname, label, col, table)
    period = "2025-01-01..2025-12-31" if col == 0 else "2024-01-01..2024-12-31"
    note_input(name, item, v, "EUR", period if "position" not in fname else ("2025-12-31" if col == 0 else "2024-12-31"),
               f"NON-SEC: adidas Annual Report 2025, {page}, row '{label}' (saved as data/raw/competitors/{fname})")
    return v * 1e6


IS = "adidas_AR2025_consolidated_income_statement_2026-10-04.html"
CF = "adidas_AR2025_consolidated_statement_of_cash_flows_2026-10-04.html"
BS = "adidas_AR2025_consolidated_statement_of_financial_position_2026-10-04.html"
ROU = "adidas_AR2025_note_right_of_use_assets_2026-10-04.html"
FIN = "adidas_AR2025_note_financial_income_financial_expenses_2026-10-04.html"
EPS = "adidas_AR2025_note_earnings_per_share_2026-10-04.html"
# Half-year reports (PDF). pdftotext turns each page into plain text with the table
# layout kept, so a row reads "Net sales   13,335   12,105   10.2% ...".
import subprocess  # noqa: E402

H1_26 = "adidas_H1_Report_2026_EN_2026-10-04.pdf"
H1_25 = "adidas_H1_Report_2025_EN_2026-10-04.pdf"
H1_URL = {H1_26: "https://res.cloudinary.com/confirmed-web/image/upload/v1785388904/adidas-group/investors/"
                 "financial-publications/2026/Q2/EN/H1_Report_2026_en_emhpcd.pdf",
          H1_25: "https://res.cloudinary.com/confirmed-web/image/upload/v1753852841/adidas-group/investors/"
                 "financial-publications/2025/Q2/H1_2025_Report_EN_Final_xvs0k3.pdf"}
pdf_text = {f: subprocess.run(["pdftotext", "-layout", str(COMP / f), "-"], capture_output=True, text=True,
                              check=True).stdout.splitlines() for f in (H1_26, H1_25)}


def adidas_pdf(fname, row_label, col, after=None):
    """The col-th number (0 = first) on the first line starting with row_label (after the line containing `after`)."""
    lines = pdf_text[fname]
    start = next(i for i, ln in enumerate(lines) if after in ln) if after else 0
    i = next(i for i in range(start, len(lines)) if lines[i].strip().startswith(row_label))
    nums = re.findall(r"\(?-?[\d,]+(?:\.\d+)?\)?%?", lines[i].strip()[len(row_label):])
    if not nums:                     # long labels wrap: the numbers sit on the next line
        nums = re.findall(r"\(?-?[\d,]+(?:\.\d+)?\)?%?", lines[i + 1])
    v = [n for n in nums if not n.endswith("%")][col]
    neg = v.startswith("(")
    v = float(v.strip("()").replace(",", ""))
    return -v if neg else v


def ah(item, fname, label, col, after, period):
    v = adidas_pdf(fname, label, col, after)
    note_input(name, item, v, "EUR", period, f"NON-SEC: adidas {'Half Year Report 2026' if fname == H1_26 else 'Half Year Report 2025'}, "
               f"'{after}', row '{label}' ({H1_URL[fname]}; saved as data/raw/competitors/{fname})")
    return v * 1e6


IS_H = "Condensed Consolidated Income Statement (IFRS)"
CF_H = "Consolidated Statement of Cash Flows (IFRS)"
BS_H = "Consolidated Statement of Financial Position (IFRS)"
EPS_H = "Earnings per share"
r = {"company": name, "report_currency": "EUR", "price_currency": "EUR", "gaap": "IFRS", "latest_period_end": "2026-06-30",
     "basis": "TTM (FY2025 annual report + H1 2026 - H1 2025), NON-SEC"}


def adidas_ttm(label, fy_label, fy_file, fy_page, after_h, table=0, fy_col=0, fy_value=None):
    """TTM = FY2025 (annual report) + H1 2026 - H1 2025 (both columns of the 2026 half-year report)."""
    fy = fy_value if fy_value is not None else ad(f"{fy_label} FY2025", fy_file, fy_label, fy_page, col=fy_col, table=table)
    h1 = ah(f"{label} H1 2026", H1_26, label, 0, after_h, "2026-01-01..2026-06-30")
    h1_prev = ah(f"{label} H1 2025", H1_26, label, 1, after_h, "2025-01-01..2025-06-30")
    return fy + h1 - h1_prev


r["revenue"] = adidas_ttm("Net sales", "Net sales", IS, f"{AR}/consolidated-income-statement.html", IS_H)
fy24 = ad("Net sales FY2024", IS, "Net sales", f"{AR}/consolidated-income-statement.html", col=1)
h1_24 = ah("Net sales H1 2024", H1_25, "Net sales", 1, IS_H, "2024-01-01..2024-06-30")
h1_25 = adidas_pdf(H1_26, "Net sales", 1, IS_H) * 1e6
r["revenue_year_ago"] = fy24 + h1_25 - h1_24
r["op_income"] = adidas_ttm("Operating profit", "Operating profit", IS, f"{AR}/consolidated-income-statement.html", IS_H)
r["da"] = adidas_ttm("Depreciation, amortization, and impairment losses", "Depreciation, amortization, and impairment",
                     CF, f"{AR}/consolidated-statement-of-cash-flows.html", CF_H)
# Net income from continuing operations attributable to shareholders: FY from the EPS note, H1 from the EPS note.
ni_fy = ad("Net income attributable to shareholders, continuing operations FY2025", EPS,
           "Net income attributable to shareholders",
           f"{AR}/notes/notes-to-the-consolidated-income-statement/earnings-per-share.html")
r["net_income"] = (ni_fy + ah("Net income attributable to shareholders, continuing operations H1 2026", H1_26,
                              "Net income/(loss) attributable to", 0, EPS_H, "2026-01-01..2026-06-30")
                   - ah("Net income attributable to shareholders, continuing operations H1 2025", H1_26,
                        "Net income/(loss) attributable to", 1, EPS_H, "2025-01-01..2025-06-30"))
# The half-year report does not split out lease depreciation and lease interest, so the FY2025
# amounts stand in for the last twelve months (lease repayments: H1 2026 EUR 339m vs H1 2025 EUR 329m,
# so the yearly lease cost barely moved).
t = pd.read_html(COMP / ROU, thousands=None)[0].map(str)
rou_row = t[t.iloc[:, 0].str.strip() == "Depreciation"].iloc[0]
rou = float([v for v in rou_row.values if v.startswith("(")][-1].strip("()").replace(",", ""))
r["rou_depreciation"] = note_input(name, "Right-of-use (lease) depreciation FY2025 (stands in for TTM)", rou, "EUR", "2025",
                                   f"NON-SEC: Annual Report 2025, note 'Right-of-use assets', total column "
                                   f"(saved as data/raw/competitors/{ROU})") * 1e6
r["lease_interest"] = ad("Interest expense on lease liabilities FY2025 (stands in for TTM)", FIN,
                         "Thereof: interest expense on lease liabilities",
                         f"{AR}/notes/notes-to-the-consolidated-income-statement/financial-income-financial-expenses.html",
                         table=1)
# Shares: adidas bought back shares until 2026-03-06, so the H1 average (176.3m) overstates today's
# count. Shares outstanding at 2026-06-30 plus the dilutive effect of share-based payments is the
# equivalent of the latest-quarter diluted average used for the other companies.
outstanding = adidas_pdf(H1_26, "Number of shares outstanding", 0)
dilutive = adidas_pdf(H1_26, "Dilutive effect of share-based", 0, EPS_H)
r["shares"] = outstanding + dilutive
note_input(name, "Shares outstanding 2026-06-30 (m)", outstanding / 1e6, "shares", "2026-06-30",
           f"NON-SEC: Half Year Report 2026, key figures, 'Number of shares outstanding' (data/raw/competitors/{H1_26})")
note_input(name, "Dilutive effect of share-based payments H1 2026 (m)", dilutive / 1e6, "shares", "2026-01-01..2026-06-30",
           "NON-SEC: Half Year Report 2026, note 05 'Earnings per share'")
r["cash"] = ah("Cash and cash equivalents 2026-06-30", H1_26, "Cash and cash equivalents", 0,
               "Consolidated Statement of Financial Position (IFRS)", "2026-06-30")
r["debt"] = (ah("Short-term borrowings 2026-06-30", H1_26, "Short-term borrowings", 0, BS_H, "2026-06-30")
             + ah("Long-term borrowings 2026-06-30", H1_26, "Long-term borrowings", 0, BS_H, "2026-06-30"))
# Non-controlling interests: the part of adidas's subsidiaries owned by outsiders. adidas's
# EBITDA includes 100% of those subsidiaries' profit, so their value belongs in enterprise value.
r["nci"] = ah("Non-controlling interests (book value) 2026-06-30", H1_26, "Non-controlling interests", 0, BS_H, "2026-06-30")
r["lease_liab"] = (ah("Current lease liabilities 2026-06-30 (check only)", H1_26, "Current lease liabilities", 0, BS_H, "2026-06-30")
                   + ah("Non-current lease liabilities 2026-06-30 (check only)", H1_26, "Non-current lease liabilities", 0,
                        BS_H, "2026-06-30"))
ah("Pensions and similar obligations 2026-06-30 (not added; noted only)", H1_26, "Pensions and similar obligations", 0,
   BS_H, "2026-06-30")
r["fixed_lease_cost"] = r["rou_depreciation"] + r["lease_interest"]
r["restructuring"] = 0.0
# 3-year growth from the ten-year overview already parsed by script 06b (continuing operations,
# Reebok excluded from 2020 on, so 2022 and 2025 are like for like).
hist = pd.read_csv(OUT / "06b_competitors_by_year.csv")
ads = hist[hist["company"] == "adidas"].set_index("calendar_year_label")
first, last = ads.loc[2025 - CAGR_YEARS, "revenue_m"], ads.loc[2025, "revenue_m"]
assert abs(last - adidas_table(IS, "Net sales")) < 1, "adidas 2025 sales differ between income statement and ten-year overview"
note_input(name, "Net sales 2022 (start of CAGR window)", first, "EUR", "2022",
           "output/06b_competitors_by_year.csv <- adidas ten-year overview (NON-SEC), continuing operations excl. Reebok")
r["cagr"] = ((last / first) ** (1 / CAGR_YEARS) - 1) * 100
r["cagr_window"] = f"FY2022 to FY2025 ({CAGR_YEARS:.2f} yrs); Reebok already excluded from 2020 on"
# Sanity checks: the half-year report's 2025 column must agree with the 2025 half-year report itself.
assert adidas_pdf(H1_25, "Net sales", 0, IS_H) * 1e6 == h1_25, "adidas H1 2025 sales differ between the two reports"
results[name] = r

# ---------------------------------------------------------------------------
# STEP 5. The multiples, every step kept as a column
# ---------------------------------------------------------------------------
rows = []
for name in ["Nike", "adidas", "Lululemon", "Deckers", "On Holding", "Under Armour"]:
    r = results[name]
    # Put the financials in the currency the shares trade in (only On differs: CHF -> USD).
    k = FX[r["report_currency"]] / FX[r["price_currency"]]
    to_usd = FX[r["price_currency"]]
    m = lambda x: x * k / 1e6          # noqa: E731  -> millions, trading currency
    price = PRICES[name]
    mcap = price * r["shares"] / 1e6
    ev = mcap + m(r["debt"]) - m(r["cash"]) + m(r["nci"])
    lease_cost = (m(r["rou_depreciation"]) + m(r["lease_interest"])) if (LEASE_ADJ and r["gaap"] == "IFRS") else 0.0
    ebitda = m(r["op_income"]) + m(r["da"]) - lease_cost
    ni = m(r["net_income"])
    rows.append({
        "company": name, "accounting": r["gaap"], "reports_in": r["report_currency"], "trades_in": r["price_currency"],
        "period": r["basis"], "latest_period_end": r["latest_period_end"],
        "share_price_2026_10_02": price,
        "diluted_shares_m": r["shares"] / 1e6,
        "market_cap_m": mcap,
        "debt_excl_leases_m": m(r["debt"]), "cash_m": m(r["cash"]), "non_controlling_interests_m": m(r["nci"]),
        "enterprise_value_m": ev,
        "revenue_ttm_m": m(r["revenue"]), "revenue_year_ago_m": m(r["revenue_year_ago"]),
        "operating_income_ttm_m": m(r["op_income"]), "d_and_a_ttm_m": m(r["da"]),
        "ifrs_lease_cost_removed_m": lease_cost,
        "ebitda_ttm_m": ebitda, "net_income_ttm_m": ni,
        "ev_to_ebitda_x": ev / ebitda if ebitda > 0 else float("nan"),
        "p_e_x": mcap / ni if ni > 0 else float("nan"),
        "revenue_growth_ttm_pct": (r["revenue"] / r["revenue_year_ago"] - 1) * 100,
        "revenue_cagr_3y_pct": r["cagr"], "cagr_window": r["cagr_window"],
        "operating_margin_ttm_pct": r["op_income"] / r["revenue"] * 100,
        "usd_per_trading_currency": to_usd,
        "market_cap_usd_m": mcap * to_usd, "enterprise_value_usd_m": ev * to_usd,
        "revenue_ttm_usd_m": m(r["revenue"]) * to_usd,
        # used only by the checks in step 5b
        "lease_liabilities_m": m(r["lease_liab"]), "fixed_lease_cost_m": m(r["fixed_lease_cost"]),
        "restructuring_ttm_m": m(r["restructuring"]),
    })
table = pd.DataFrame(rows)

# Peer median (Nike left out), so Nike can be read against "a typical competitor".
peers = table[table["company"] != "Nike"]
med = {"company": "Peer median (excl. Nike)"}
for c in ["ev_to_ebitda_x", "p_e_x", "revenue_growth_ttm_pct", "revenue_cagr_3y_pct", "operating_margin_ttm_pct"]:
    med[c] = peers[c].median()
table = pd.concat([table, pd.DataFrame([med])], ignore_index=True)

table.round(4).to_csv(OUT / "08_peer_multiples.csv", index=False)
pd.DataFrame(inputs).round(4).to_csv(OUT / "08_peer_inputs.csv", index=False)

# ---------------------------------------------------------------------------
# STEP 5b. Checks: factors the main table leaves out, each switched on one at a time
# ---------------------------------------------------------------------------
# Each row says what changes, and the multiple before and after, so you can see
# whether that factor moves the conclusion.
co = table.set_index("company")
checks = []


def check(company, factor, metric, before, after, how):
    checks.append({"company": company, "factor": factor, "metric": metric, "base_case": before, "with_factor": after,
                   "change_pct": (after / before - 1) * 100 if before == before and after == after else float("nan"),
                   "how_calculated": how})


# 1. Leases counted as debt for everyone: EV + lease liabilities, over EBITDA + fixed rent (EBITDAR).
for c in co.index[co.index != "Peer median (excl. Nike)"]:
    x = co.loc[c]
    ebitdar = x["ebitda_ttm_m"] + x["fixed_lease_cost_m"]
    after = (x["enterprise_value_m"] + x["lease_liabilities_m"]) / ebitdar if ebitdar > 0 else float("nan")
    check(c, "Leases treated as debt", "EV / EBITDA (x)", x["ev_to_ebitda_x"], after,
          f"(EV {x['enterprise_value_m']:,.0f} + lease liabilities {x['lease_liabilities_m']:,.0f}) / "
          f"(EBITDA {x['ebitda_ttm_m']:,.0f} + fixed lease cost {x['fixed_lease_cost_m']:,.0f})")
# 2. adidas without the IFRS lease fix, and without non-controlling interests.
x = co.loc["adidas"]
check("adidas", "No IFRS lease fix (raw IFRS EBITDA)", "EV / EBITDA (x)", x["ev_to_ebitda_x"],
      x["enterprise_value_m"] / (x["ebitda_ttm_m"] + x["ifrs_lease_cost_removed_m"]),
      "EV / (operating profit + all D&A); rent is then not counted as a cost")
check("adidas", "Non-controlling interests left out of EV", "EV / EBITDA (x)", x["ev_to_ebitda_x"],
      (x["enterprise_value_m"] - x["non_controlling_interests_m"]) / x["ebitda_ttm_m"],
      f"EV without EUR {x['non_controlling_interests_m']:,.0f}m minority stakes (the first version of this table)")
# 3. On's CHF figures at the average rate of its twelve months instead of the 2026-10-02 rate.
x = co.loc["On Holding"]
fx_ratio = A.CHECK_ON_FX_AVERAGE_RATE["value"] / FX["CHF"]
ev_avg = x["market_cap_m"] + (x["debt_excl_leases_m"] - x["cash_m"])        # balance sheet stays at spot
check("On Holding", "CHF profits at the average 12-month rate", "EV / EBITDA (x)", x["ev_to_ebitda_x"],
      ev_avg / (x["ebitda_ttm_m"] * fx_ratio), f"EBITDA x {fx_ratio:.4f} (average {A.CHECK_ON_FX_AVERAGE_RATE['value']} / spot {FX['CHF']})")
check("On Holding", "CHF profits at the average 12-month rate", "P / E (x)", x["p_e_x"],
      x["market_cap_m"] / (x["net_income_ttm_m"] * fx_ratio), "net income x the same ratio")
# 4. Under Armour before restructuring and impairment charges.
x = co.loc["Under Armour"]
ebitda_ex = x["ebitda_ttm_m"] + x["restructuring_ttm_m"]
check("Under Armour", "Restructuring and impairment charges added back", "EV / EBITDA (x)", float("nan"),
      x["enterprise_value_m"] / ebitda_ex if ebitda_ex > 0 else float("nan"),
      f"EBITDA {x['ebitda_ttm_m']:,.0f} + charges {x['restructuring_ttm_m']:,.0f} = {ebitda_ex:,.0f}")
check("Under Armour", "Restructuring and impairment charges added back", "Operating margin (%)", x["operating_margin_ttm_pct"],
      (x["operating_income_ttm_m"] + x["restructuring_ttm_m"]) / x["revenue_ttm_m"] * 100, "same add-back")
checks = pd.DataFrame(checks)
checks.round(3).to_csv(OUT / "08_peer_checks.csv", index=False)

# ---------------------------------------------------------------------------
# STEP 5c. What the peer multiples say Nike is worth, next to the DCF and the price
# ---------------------------------------------------------------------------
# Value per share = (peer multiple x Nike's TTM profit - debt + cash) / shares.
# For P/E there is no debt step: peer P/E x Nike net income = equity value.
nk = co.loc["Nike"]
peer_rows = co.drop(index=["Nike", "Peer median (excl. Nike)"])
lease_check = checks[checks["factor"] == "Leases treated as debt"].set_index("company")["with_factor"]
dcf_value = pd.read_csv(OUT / "06_base_case_check.csv").set_index("item").loc["Value per share, base case (USD)", "dcf_model_py"]
net_debt = nk["debt_excl_leases_m"] - nk["cash_m"]
sh = nk["diluted_shares_m"]
vals = []


def from_multiple(label, multiple, profit, minus_net_debt, extra_debt=0.0, how=""):
    equity = multiple * profit - (net_debt + extra_debt if minus_net_debt else 0.0)
    vals.append({"method": label, "multiple_x": multiple, "nike_profit_usd_m": profit, "equity_value_usd_m": equity,
                 "value_per_share_usd": equity / sh, "vs_price_pct": (equity / sh / PRICES["Nike"] - 1) * 100,
                 "how_calculated": how})


for stat in ("median", "min", "max"):
    ev_m = getattr(peer_rows["ev_to_ebitda_x"].dropna(), stat)()
    from_multiple(f"Peer {stat} EV/EBITDA", ev_m, nk["ebitda_ttm_m"], True,
                  how="multiple x Nike TTM EBITDA - debt + cash, / diluted shares")
for stat in ("median", "min", "max"):
    pe = getattr(peer_rows["p_e_x"].dropna(), stat)()
    from_multiple(f"Peer {stat} P/E", pe, nk["net_income_ttm_m"], False, how="multiple x Nike TTM net income, / diluted shares")
ebitdar_nk = nk["ebitda_ttm_m"] + nk["fixed_lease_cost_m"]
from_multiple("Peer median EV/EBITDAR (leases as debt)", lease_check.drop("Nike").median(), ebitdar_nk, True,
              extra_debt=nk["lease_liabilities_m"], how="multiple x Nike EBITDAR - debt - lease liabilities + cash, / shares")
vals.append({"method": "DCF base case (output/05_valuation.csv)", "value_per_share_usd": dcf_value,
             "vs_price_pct": (dcf_value / PRICES["Nike"] - 1) * 100,
             "multiple_x": (dcf_value * sh + net_debt) / nk["ebitda_ttm_m"], "nike_profit_usd_m": nk["ebitda_ttm_m"],
             "equity_value_usd_m": dcf_value * sh,
             "how_calculated": "EV/EBITDA the DCF value implies on Nike's TTM EBITDA"})
vals.append({"method": "DCF base case, as P/E", "value_per_share_usd": dcf_value,
             "vs_price_pct": (dcf_value / PRICES["Nike"] - 1) * 100,
             "multiple_x": dcf_value * sh / nk["net_income_ttm_m"], "nike_profit_usd_m": nk["net_income_ttm_m"],
             "equity_value_usd_m": dcf_value * sh, "how_calculated": "P/E the DCF value implies on Nike's TTM net income"})
vals.append({"method": "Share price 2026-10-02", "value_per_share_usd": PRICES["Nike"], "vs_price_pct": 0.0,
             "multiple_x": nk["ev_to_ebitda_x"], "nike_profit_usd_m": nk["ebitda_ttm_m"],
             "equity_value_usd_m": nk["market_cap_m"], "how_calculated": "Nike's actual EV/EBITDA"})
nike_vals = pd.DataFrame(vals)
nike_vals.round(3).to_csv(OUT / "08_nike_value_from_peers.csv", index=False)
print(checks[["company", "factor", "metric", "base_case", "with_factor", "change_pct"]].round(2).to_string(index=False))
print(nike_vals[["method", "multiple_x", "value_per_share_usd", "vs_price_pct"]].round(2).to_string(index=False))

show = table[["company", "ev_to_ebitda_x", "p_e_x", "revenue_growth_ttm_pct", "revenue_cagr_3y_pct",
              "operating_margin_ttm_pct", "market_cap_usd_m", "enterprise_value_usd_m"]]
print(show.round(1).to_string(index=False))

# ---------------------------------------------------------------------------
# STEP 6. Excel version with live formulas, so each multiple can be traced by clicking
# ---------------------------------------------------------------------------
from openpyxl import Workbook                                  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill       # noqa: E402
from openpyxl.utils import get_column_letter                   # noqa: E402

wb = Workbook()
ws = wb.active
ws.title = "Comparison"
blue, bold = Font(color="0000FF"), Font(bold=True)
head_fill = PatternFill("solid", fgColor="DDE4EE")
nike_fill = PatternFill("solid", fgColor="FFF2CC")

ws["A1"] = f"Nike vs peers: valuation multiples at share prices of {PRICE_DATE}"
ws["A1"].font = Font(bold=True, size=13)
ws["A2"] = ("Blue = number copied from a filing or price source (see Inputs sheet); black = Excel formula. "
            "Money in millions of the currency the shares trade in (On converted from CHF to USD).")
# (header, column id, value key or formula). In formulas, {id} becomes that column's cell in the same row.
cols = [
    ("Company", "co", "company"), ("Accounting", "acc", "accounting"), ("Period", "per", "period"),
    ("Latest period end", "end", "latest_period_end"), ("Trades in", "cur", "trades_in"),
    ("Share price", "px", "share_price_2026_10_02"), ("Diluted shares (m)", "sh", "diluted_shares_m"),
    ("Market cap (m)", "mc", "={px}*{sh}"), ("Debt excl. leases (m)", "debt", "debt_excl_leases_m"), ("Cash (m)", "cash", "cash_m"),
    ("Non-controlling interests (m)", "nci", "non_controlling_interests_m"),
    ("Enterprise value (m)", "ev", "={mc}+{debt}-{cash}+{nci}"),
    ("Revenue TTM (m)", "rev", "revenue_ttm_m"), ("Revenue year earlier (m)", "rev0", "revenue_year_ago_m"),
    ("Operating income TTM (m)", "oi", "operating_income_ttm_m"), ("D&A TTM (m)", "da", "d_and_a_ttm_m"),
    ("IFRS lease cost removed (m)", "lease", "ifrs_lease_cost_removed_m"),
    ("EBITDA TTM (m)", "ebitda", "={oi}+{da}-{lease}"), ("Net income TTM (m)", "ni", "net_income_ttm_m"),
    ("EV / EBITDA (x)", "evx", '=IF({ebitda}>0,{ev}/{ebitda},"n.m.")'), ("P / E (x)", "pe", '=IF({ni}>0,{mc}/{ni},"n.m.")'),
    ("Revenue growth TTM (%)", "g", "=({rev}/{rev0}-1)*100"), ("Revenue CAGR 3y (%)", "cagr", "revenue_cagr_3y_pct"),
    ("Operating margin TTM (%)", "om", "={oi}/{rev}*100"), ("USD per trading-currency unit", "fx", "usd_per_trading_currency"),
    ("Market cap (USD m)", "mcusd", "={mc}*{fx}"), ("Enterprise value (USD m)", "evusd", "={ev}*{fx}"),
    ("CAGR window", "win", "cagr_window"),
]
L = {cid: get_column_letter(j) for j, (_, cid, _) in enumerate(cols, 1)}
HR = 4
for j, (h, _, _) in enumerate(cols, 1):
    c = ws.cell(row=HR, column=j, value=h)
    c.font, c.fill, c.alignment = bold, head_fill, Alignment(wrap_text=True, vertical="top")
companies = table[table["company"] != "Peer median (excl. Nike)"].reset_index(drop=True)
for i, rec in companies.iterrows():
    rr = HR + 1 + i
    for j, (_, _, key) in enumerate(cols, 1):
        if key.startswith("="):
            ws.cell(row=rr, column=j, value=key.format(**{k: f"{v}{rr}" for k, v in L.items()}))
        else:
            c = ws.cell(row=rr, column=j, value=rec[key])
            if isinstance(rec[key], float):
                c.font = blue
        if rec["company"] == "Nike":
            ws.cell(row=rr, column=j).fill = nike_fill
last = HR + len(companies)
mr = last + 1
ws.cell(row=mr, column=1, value="Peer median (excl. Nike)").font = bold
for col_letter in [L[k] for k in ("evx", "pe", "g", "cagr", "om")]:
    ws[f"{col_letter}{mr}"] = f"=MEDIAN({col_letter}{HR + 2}:{col_letter}{last})"   # Nike is the first data row
    ws[f"{col_letter}{mr}"].font = bold
for j in range(1, len(cols) + 1):
    ws.column_dimensions[get_column_letter(j)].width = 14
ws.column_dimensions["A"].width = 24
ws.column_dimensions["C"].width = 30
ws.column_dimensions[L["win"]].width = 40
for row in ws.iter_rows(min_row=HR + 1, max_row=mr):
    for c in row:
        if 6 <= c.column < len(cols):
            c.number_format = "#,##0.0"
ws.freeze_panes = "B5"

wi = wb.create_sheet("Inputs")
inp = pd.DataFrame(inputs)
for j, h in enumerate(inp.columns, 1):
    wi.cell(row=1, column=j, value=h).font = bold
for i, rec in enumerate(inp.itertuples(index=False), 2):
    for j, v in enumerate(rec, 1):
        wi.cell(row=i, column=j, value=v)
for col, w in zip("ABCDEF", (14, 52, 14, 9, 24, 140)):
    wi.column_dimensions[col].width = w

for title, frame in (("Checks", checks), ("Nike value from peers", nike_vals)):
    wc = wb.create_sheet(title)
    for j, h in enumerate(frame.columns, 1):
        wc.cell(row=1, column=j, value=h).font = bold
    for i, rec in enumerate(frame.itertuples(index=False), 2):
        for j, v in enumerate(rec, 1):
            wc.cell(row=i, column=j, value=None if (isinstance(v, float) and v != v) else v)
            if isinstance(v, float):
                wc.cell(row=i, column=j).number_format = "#,##0.00"
    for j in range(1, len(frame.columns) + 1):
        wc.column_dimensions[get_column_letter(j)].width = 22
    wc.column_dimensions[get_column_letter(len(frame.columns))].width = 100

wn = wb.create_sheet("Notes")
notes = [
    "How to read this workbook",
    "EV / EBITDA: enterprise value (shares + debt - cash + non-controlling interests, leases excluded) divided by EBITDA over the last twelve months.",
    "Non-controlling interests: adidas's EBITDA includes 100% of subsidiaries it only partly owns, so outsiders' stakes (book value) are added to EV.",
    "Checks sheet: each factor the main table leaves out, switched on alone. Nike value from peers: peer multiples applied to Nike's profit.",
    "P / E: market cap divided by net income attributable to shareholders over the last twelve months.",
    "TTM = latest fiscal year + year to date - prior year to date, from each company's latest 10-Q / 6-K.",
    "adidas (NON-SEC): TTM = Annual Report 2025 + Half Year Report 2026 - H1 2025; balance sheet at 2026-06-30. "
    "Its lease depreciation and lease interest are FY2025 amounts (the half-year report does not split them out).",
    "IFRS lease adjustment (adidas, On): EBITDA = operating profit + D&A - right-of-use depreciation - lease interest, "
    "so rent counts as an operating cost as it does under US GAAP. Operating margin is as reported.",
    "adidas D&A includes impairment losses (EUR 1,154m line of the cash flow statement).",
    "On Holding: CHF figures converted to USD at " + str(FX["CHF"]) + " (2026-10-02). Class B shares count as 1/10 of a class A share.",
    "Under Armour: class A price (UAA) applied to all classes; class C (UA) closed 2.5% lower, so market cap is slightly high.",
    "Under Armour's fiscal year runs April to March (since 2022); Deckers' also ends in March, Lululemon's in late January/early February.",
    "Nike: operating income = gross profit - S&A (Nike reports no operating income line); balance sheet and shares as in the DCF.",
    "Sources: see Inputs sheet (form, accession number, filed date for every SEC number). Script: scripts/08_peer_multiples.py.",
]
for i, n in enumerate(notes, 1):
    wn.cell(row=i, column=1, value=n).font = bold if i == 1 else Font()
wn.column_dimensions["A"].width = 160
wb.save(OUT / "08_peer_multiples.xlsx")
print("Saved output/08_peer_multiples.csv/.xlsx, 08_peer_inputs.csv, 08_peer_checks.csv, 08_nike_value_from_peers.csv")
