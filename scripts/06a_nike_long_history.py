"""
06a_nike_long_history.py  -  Nike's revenue growth and operating margin back to FY1993, from SEC filings

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
The rest of the project only looks at FY2017-FY2026. To answer "has Nike ever
been in a slump like this, and how long did the recovery take?" we need a much
longer record. This script builds one, using only SEC filings:

  1. FY1993-FY2007: Nike's old 10-K annual reports on SEC EDGAR. Each 10-K has an
     income statement with three years side by side, so six filings (FY1995,
     1997, 2000, 2003, 2006, 2009) cover FY1993-FY2009. The script downloads each
     full filing (once) into data/raw/10k_history/ and reads three lines from its
     income statement: Revenues, Cost of sales, Selling and administrative.
  2. FY2008-FY2026: the SEC's XBRL "company facts" file the project already
     downloaded (data/raw/companyfacts_...json).
  When two filings report the same year, the most recently filed one wins (it
  includes any later restatement), the same rule script 01 uses.

Operating income is defined as in the rest of the project:
    operating income = revenue - cost of sales - selling & administrative
                     = gross profit - selling & administrative
In most years that IS Nike's full operating cost: since FY2010, restructuring
and impairment costs sit inside S&A (e.g. FY2024's USD 443m restructuring). But in
FY1998-FY2000 and FY2009 Nike showed one-offs on separate lines below S&A
(restructuring, goodwill and intangible impairments). So the table has two margins:
  operating margin                      = (gross profit - S&A) / revenue, the DCF's definition
  operating margin incl. one-offs       = (gross profit - S&A - those separate lines) / revenue,
                                          the "as reported" basis that competitors' figures use

Then it finds Nike's past slumps and measures how long each recovery took
(STEP 5): a slump starts in a year when revenue fell or the operating margin
dropped by 2 points or more, and consecutive bad years count as one slump.

Outputs
  output/06a_nike_history_fy1993_fy2026.csv     one row per fiscal year, with the filing behind each number
  output/06a_nike_downturns_and_recoveries.csv  each past slump and how many years recovery took
"""

import html
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data/raw/10k_history"
COMPANYFACTS = ROOT / "data/raw/companyfacts_CIK0000320187_2026-10-04.json"
OUT_CSV = ROOT / "output/06a_nike_history_fy1993_fy2026.csv"

# The SEC's www.sec.gov/Archives server refuses requests whose User-Agent has no
# contact e-mail. Set your own with:  export SEC_USER_AGENT="your-name you@yourmail.com"
# The default below is the placeholder suggested in scripts 01 and 01b.
USER_AGENT = os.environ.get("SEC_USER_AGENT", "nike-valuation-project you@example.com")

# Older 10-K filings (accession number -> fiscal year it reports). Taken from the
# SEC filing index, https://data.sec.gov/submissions/CIK0000320187-submissions-00{1,2}.json
OLD_10KS = {
    "0000320187-95-000013": 1995,
    "0000912057-97-029601": 1997,
    "0000912057-00-039514": 2000,   # form 10-K405 (same content as a 10-K)
    "0001193125-03-031022": 2003,
    "0001193125-06-156152": 2006,
    "0001193125-09-155951": 2009,
}


# ---------------------------------------------------------------------------
# STEP 1. Download each old 10-K once (skip if the file is already there)
# ---------------------------------------------------------------------------
def raw_path(accn):
    return RAW_DIR / f"nke_10k_full_submission_{accn}.txt"


RAW_DIR.mkdir(parents=True, exist_ok=True)
for accn in OLD_10KS:
    p = raw_path(accn)
    if not p.exists():
        url = f"https://www.sec.gov/Archives/edgar/data/320187/{accn}.txt"
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
        r.raise_for_status()
        p.write_bytes(r.content)
        time.sleep(0.5)           # be polite to the SEC server


# ---------------------------------------------------------------------------
# STEP 2. Read the income statement out of each old filing
# ---------------------------------------------------------------------------
# The filings are plain text (1990s) or HTML (2000s). We strip HTML tags, find the
# heading "STATEMENT(S) OF INCOME", and in the text right after it take the first
# three numbers after each line label. Those are the three fiscal years, newest first.
NUM = r"\(?\$?\s*\|?\s*[\d,]+\.?\d*"


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text)        # drop HTML tags
    text = html.unescape(text)
    text = text.replace("$0,", "$ ")            # the FY1995 filing prints "$0,399,664" for "$399,664"
    return re.sub(r"[ \t\xa0|]+", " ", text)


def three_numbers_after(block, label):
    m = re.search(label, block)
    if not m:
        raise ValueError(f"label {label!r} not found")
    nums = re.findall(r"\d[\d,]*\.?\d*", block[m.end(): m.end() + 400])
    nums = [n for n in nums if "," in n or "." in n]  # skip note numbers like "(Note 6)"
    return [float(n.replace(",", "")) for n in nums[:3]]


def optional_three(block, label):
    """Like three_numbers_after, for a line that may be missing; dashes count as 0, (x) as -x."""
    m = re.search(label, block)
    if not m:
        return [0.0, 0.0, 0.0]
    toks = re.findall(r"\(\s*[\d,]+\.\d+\s*\)?|[\d,]+\.\d+|—|--", block[m.end(): m.end() + 200])[:3]
    out = []
    for t in toks:
        if t in ("—", "--"):
            out.append(0.0)
        else:
            out.append(-float(t.strip("() ").replace(",", "")) if t.startswith("(") else float(t.replace(",", "")))
    return out


ONE_OFF_LABELS = [r"Restructuring charges?(, net)?", r"Goodwill impairment", r"Intangible and other asset impairment"]

rows = []
for accn, fy in OLD_10KS.items():
    text = clean(raw_path(accn).read_text(errors="ignore"))
    start = re.search(r"STATEMENTS? OF INCOME", text).start()
    block = text[start: start + 4000]
    # 1990s filings are in thousands of dollars, later ones in millions.
    scale = 1 / 1000 if re.search(r"IN THOUSANDS", block, re.I) else 1
    revenue = three_numbers_after(block, r"Revenues")
    cogs = three_numbers_after(block, r"Costs? of sales")
    sga = three_numbers_after(block, r"Selling and administrative")
    statement = block[: re.search(r"Net income", block).start()]       # stop at the bottom line
    one_offs = [sum(x) for x in zip(*[optional_three(statement, lab) for lab in ONE_OFF_LABELS])]
    for k in range(3):                      # k=0 is the filing's own year, 1 and 2 the years before
        rows.append({
            "fiscal_year": fy - k,
            "revenue_usd_m": revenue[k] * scale,
            "gross_profit_usd_m": (revenue[k] - cogs[k]) * scale,
            "sga_usd_m": sga[k] * scale,
            "one_offs_below_sga_usd_m": one_offs[k] * scale,
            "source": f"10-K for FY{fy}, accession {accn} (income statement, read from text)",
            "filing_rank": fy,               # later filing = higher rank = wins
        })

# ---------------------------------------------------------------------------
# STEP 3. FY2008 onward from the SEC XBRL company facts file
# ---------------------------------------------------------------------------
facts = json.loads(COMPANYFACTS.read_text())["facts"]["us-gaap"]


def annual(tags):
    """Full-year values from 10-K filings for any of the given tags; latest filing wins per year."""
    out = {}
    for tag in tags:
        for x in facts.get(tag, {}).get("units", {}).get("USD", []):
            if x.get("form") != "10-K" or not x["end"].endswith("05-31"):
                continue
            days = (pd.Timestamp(x["end"]) - pd.Timestamp(x["start"])).days
            if not 360 <= days <= 370:      # keep full-year figures only
                continue
            fy = int(x["end"][:4])
            if fy not in out or x["filed"] > out[fy][1]:
                out[fy] = (x["val"] / 1e6, x["filed"], x["accn"], tag)
    return out


rev = annual(["SalesRevenueNet", "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])
gp = annual(["GrossProfit"])
sga = annual(["SellingGeneralAndAdministrativeExpense"])
for fy in sorted(set(rev) & set(gp) & set(sga)):
    rows.append({
        "fiscal_year": fy,
        "revenue_usd_m": rev[fy][0],
        "gross_profit_usd_m": gp[fy][0],
        "sga_usd_m": sga[fy][0],
        "source": f"SEC XBRL company facts, 10-K accession {rev[fy][2]} filed {rev[fy][1]} (revenue tag {rev[fy][3]})",
        "filing_rank": 10_000,               # XBRL figures are the latest restated ones, so they win
    })

# ---------------------------------------------------------------------------
# STEP 4. One row per year (latest filing wins), then growth and margin
# ---------------------------------------------------------------------------
df = (pd.DataFrame(rows).sort_values(["fiscal_year", "filing_rank"])
      .groupby("fiscal_year").tail(1).set_index("fiscal_year").sort_index())
# XBRL rows have no one-off column: FY2008+ one-offs are inside S&A, except FY2009,
# which comes from the FY2009 10-K text above (an older filing, so fill it in by year).
text_one_offs = pd.DataFrame(rows).dropna(subset=["one_offs_below_sga_usd_m"]).groupby("fiscal_year")["one_offs_below_sga_usd_m"].last()
df["one_offs_below_sga_usd_m"] = text_one_offs.reindex(df.index).fillna(0.0)
df["operating_income_usd_m"] = df["gross_profit_usd_m"] - df["sga_usd_m"]
df["operating_income_incl_one_offs_usd_m"] = df["operating_income_usd_m"] - df["one_offs_below_sga_usd_m"]
df["revenue_growth_pct"] = df["revenue_usd_m"].pct_change() * 100
df["operating_margin_pct"] = df["operating_income_usd_m"] / df["revenue_usd_m"] * 100
df["operating_margin_incl_one_offs_pct"] = df["operating_income_incl_one_offs_usd_m"] / df["revenue_usd_m"] * 100
df = df.drop(columns="filing_rank").round(2)
cols = ["revenue_usd_m", "gross_profit_usd_m", "sga_usd_m", "operating_income_usd_m", "one_offs_below_sga_usd_m",
        "operating_income_incl_one_offs_usd_m", "revenue_growth_pct", "operating_margin_pct",
        "operating_margin_incl_one_offs_pct", "source"]
df[cols].to_csv(OUT_CSV)
print(df[["revenue_usd_m", "operating_income_usd_m", "one_offs_below_sga_usd_m", "revenue_growth_pct",
          "operating_margin_pct", "operating_margin_incl_one_offs_pct"]].to_string())
print(f"\nSaved {OUT_CSV.relative_to(ROOT)}")

# ---------------------------------------------------------------------------
# STEP 5. Past slumps and how long the recovery took
# ---------------------------------------------------------------------------
# A "bad year": revenue fell, or operating margin dropped 2+ percentage points.
# (2 points is our judgment for "a real drop", not a modeling assumption, so it is set here.)
MARGIN_DROP_PTS = 2.0
bad = (df["revenue_growth_pct"] < 0) | (df["operating_margin_pct"].diff() <= -MARGIN_DROP_PTS)
years = list(df.index)
episodes, current = [], []
for y in years:
    if bad.get(y, False):
        current.append(y)
    elif current:
        episodes.append(current); current = []
if current:
    episodes.append(current)


def first_year(cond_years):
    return cond_years[0] if cond_years else None


out = []
for ep in episodes:
    before = ep[0] - 1                                   # last good year before the slump
    pre_rev = df.loc[:ep[-1], "revenue_usd_m"].max()     # highest revenue up to the end of the slump
    pre_margin = df.loc[before, "operating_margin_pct"]
    after = df.loc[ep[0]:]
    trough = after.loc[:ep[-1] + 1, "operating_margin_pct"].idxmin()
    rev_back = first_year([y for y in after.index if y > ep[-1] and after.loc[y, "revenue_usd_m"] > pre_rev])
    margin_back = first_year([y for y in after.index if y > trough and after.loc[y, "operating_margin_pct"] >= pre_margin - 1])
    out.append({
        "slump_years": f"FY{ep[0]}" + (f"-FY{ep[-1]}" if len(ep) > 1 else ""),
        "pre_slump_year": before,
        "pre_slump_margin_pct": pre_margin,
        "trough_year": trough,
        "trough_margin_pct": df.loc[trough, "operating_margin_pct"],
        "worst_revenue_growth_pct": df.loc[ep, "revenue_growth_pct"].min(),
        "year_of_new_revenue_high": rev_back,
        "years_from_slump_start_to_new_revenue_high": (rev_back - ep[0]) if rev_back else None,
        "year_margin_back_within_1pt": margin_back,
        "years_from_trough_to_margin_back": (margin_back - trough) if margin_back else None,
    })
rec = pd.DataFrame(out)
rec.to_csv(ROOT / "output/06a_nike_downturns_and_recoveries.csv", index=False)
print("\nPast slumps:\n" + rec.to_string(index=False))
