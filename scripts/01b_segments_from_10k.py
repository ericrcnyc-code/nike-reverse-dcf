"""
01b_segments_from_10k.py  -  Segment and channel revenue, read from Nike's 10-K documents

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
1. Downloads Nike's annual reports (10-Ks) for fiscal 2017-2026 from sec.gov and
   saves them untouched in data/raw/10k/. These are the same documents a person
   would read; the SEC's company-facts API (used in 01_download.py) does not
   carry the segment split cleanly.
2. Turns each document into plain text, then reads specific rows out of
   specific tables: revenue for each geography (North America, Europe/Middle
   East/Africa, Greater China, Asia Pacific/Latin America), Converse, and
   the split between sales to wholesale customers and NIKE Direct (Nike's own
   stores and websites).
3. Every number is saved with its receipt: which 10-K, which section, and which
   printed page of that 10-K it is on, so you can open the filing and check.
4. Runs checks: the pieces must add up to the totals Nike prints, and total
   revenue must match the SEC API numbers from 01_download.py. Also checks
   revenue and net income against each 10-K's income statement.

WHICH 10-K IS USED FOR EACH YEAR
--------------------------------
Each 10-K shows three years. When Nike re-cuts its segments, older years are
restated in newer filings, so for each year we use the NEWEST 10-K that shows
it (same rule as 01_download.py). FY2019-FY2026 come from the "Revenues" note
(the revenue disaggregation table). FY2017-FY2018 predate that note, so they
come from the "Operating segments" note (segment totals) and the per-geography
tables in Item 7 (MD&A) for the wholesale / direct split.

HOW TO RUN
----------
    export SEC_USER_AGENT="nike-valuation-project you@example.com"
    python3 scripts/01b_segments_from_10k.py
"""

import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# DOWNLOAD SETTINGS (not modeling assumptions)
# ---------------------------------------------------------------------------
USER_AGENT = os.environ.get("SEC_USER_AGENT", "nike-valuation-project personal-research")
PROJECT = Path(__file__).resolve().parent.parent
RAW_10K = PROJECT / "data" / "raw" / "10k"
PROCESSED = PROJECT / "data" / "processed"

# Nike's 10-K filings: fiscal year -> (accession number, filed date, document).
# Taken from the SEC's filing index, https://data.sec.gov/submissions/CIK0000320187.json
FILINGS = {
    2026: ("0000320187-26-000088", "2026-07-15", "nke-20260531.htm"),
    2025: ("0000320187-25-000047", "2025-07-17", "nke-20250531.htm"),
    2024: ("0000320187-24-000044", "2024-07-25", "nke-20240531.htm"),
    2023: ("0000320187-23-000039", "2023-07-20", "nke-20230531.htm"),
    2022: ("0000320187-22-000038", "2022-07-21", "nke-20220531.htm"),
    2021: ("0000320187-21-000028", "2021-07-20", "nke-20210531.htm"),
    2020: ("0000320187-20-000047", "2020-07-24", "nke-531202010k.htm"),
    2019: ("0000320187-19-000051", "2019-07-23", "nke-531201910k.htm"),
    2018: ("0000320187-18-000142", "2018-07-25", "nke-5312018x10k.htm"),
    2017: ("0000320187-17-000090", "2017-07-20", "nke-5312017x10k.htm"),
}

# Short names for the columns Nike prints, in our output.
SEGMENT_NAMES = {
    "NORTH AMERICA": "North America",
    "EUROPE, MIDDLE EAST & AFRICA": "EMEA",
    "GREATER CHINA": "Greater China",
    "ASIA PACIFIC & LATIN AMERICA": "APLA",
    "GLOBAL BRAND DIVISIONS": "Global Brand Divisions",
    "TOTAL NIKE BRAND": "Total NIKE Brand",
    "CONVERSE": "Converse",
    "CORPORATE": "Corporate",
    "TOTAL NIKE, INC.": "Total NIKE, Inc.",
}


# ---------------------------------------------------------------------------
# STEP 1: download each 10-K (once) and turn it into plain text
# ---------------------------------------------------------------------------
def url_for(fy):
    accn, _, doc = FILINGS[fy]
    return f"https://www.sec.gov/Archives/edgar/data/320187/{accn.replace('-', '')}/{doc}"


def load_text(fy):
    """Return the 10-K as one long string. Table cells are separated by ' | '
    and each table row ends with a line break, so rows can be read in order."""
    RAW_10K.mkdir(parents=True, exist_ok=True)
    path = RAW_10K / f"nke_10k_{FILINGS[fy][2]}"
    if not path.exists():
        print(f"Downloading FY{fy} 10-K: {url_for(fy)}")
        r = requests.get(url_for(fy), headers={"User-Agent": USER_AGENT}, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)      # saved exactly as downloaded
        time.sleep(0.3)                  # be polite to the SEC's servers
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    for tr in soup.find_all("tr"):
        tr.append("\n")
    for td in soup.find_all("td"):
        td.append(" | ")
    text = soup.get_text("\n").replace("\xa0", " ")
    text = re.sub(r"(\s*\|\s*)+", " | ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    # Footnote markers like "(3)" sit on their own line after a row label;
    # drop them so they aren't read as the number -3.
    text = re.sub(r"\n\(\d\)\s*\|", " |", text)
    # Negatives are sometimes split across cells or lines: "(7 | )" in older
    # filings, "(\n97\n)" in newer ones. Rejoin both to "(7)" / "(97)".
    text = re.sub(r"\(\s*(\d[\d,]*)\s*(?:\|\s*)?\)", r"(\1)", text)
    return text


# ---------------------------------------------------------------------------
# STEP 2: small helpers to read a row and find its page
# ---------------------------------------------------------------------------
def to_number(tok):
    """'1,234' -> 1234, '(97)' -> -97, '—' -> 0 (Nike prints a dash for zero)."""
    tok = tok.strip()
    if tok in {"—", "-", "–"}:
        return 0.0
    neg = tok.startswith("(") and tok.endswith(")")
    return float(tok.strip("()").replace(",", "")) * (-1 if neg else 1)


def row_values(text, start, label, end=None):
    """Find the first row called `label` after position `start` (and before
    `end`), and return (its numbers in printed order, position of the row).
    '$' and '%' cells are skipped; reading stops at the next text label."""
    pos = text.find(f"| {label} |", start, end)
    if pos < 0 and text.find(f"\n{label} |", start, end) >= 0:
        pos = text.find(f"\n{label} |", start, end)
    if pos < 0:
        raise ValueError(f"row '{label}' not found")
    vals = []
    for tok in text[pos + len(label) + 3:].split("|"):
        tok = tok.strip()
        if tok in {"$", "%", ""}:
            continue
        if re.fullmatch(r"\(?-?[\d,]+(\.\d+)?\)?|—|–", tok):
            vals.append(to_number(tok))
        else:
            break                          # reached the next row's label
    return vals, pos


def page_at(text, pos):
    """Printed page number of the page containing `pos`: the page number Nike
    prints at the bottom of each page is the first one after `pos`."""
    m = re.search(r"\n(\d{1,3})\s*\n\s*(?:Table of Contents|$)", text[pos:])
    return int(m.group(1)) if m else None


def section_at(text, pos):
    """Nearest heading before `pos`: a 'NOTE n — ...' title or 'ITEM 7'."""
    notes = list(re.finditer(r"NOTE \d+ — [A-Z ,&\-]+", text[:pos]))
    item7 = text.rfind("ITEM 7. MANAGEMENT", 0, pos)
    if notes and notes[-1].start() > item7:
        return notes[-1].group(0).strip()
    return "Item 7 (MD&A)"


def record(rows, fy, segment, measure, value, filing_fy, text, pos, table):
    accn, filed, _ = FILINGS[filing_fy]
    rows.append({
        "fiscal_year": fy, "segment": segment, "measure": measure,
        "value_usd_millions": value,
        "source_10k": f"FY{filing_fy} 10-K", "accession_number": accn,
        "filed": filed, "section": section_at(text, pos),
        "table": table, "page": page_at(text, pos), "url": url_for(filing_fy),
    })


# ---------------------------------------------------------------------------
# STEP 3a: FY2019-FY2026 from the "Revenues" note (one table per year)
# ---------------------------------------------------------------------------
def from_revenue_note(texts, rows):
    done = set()
    for filing_fy in sorted(FILINGS, reverse=True):          # newest first
        text = texts[filing_fy]
        heads = list(re.finditer(
            r"YEAR ENDED MAY 31, (20\d\d) \| \(Dollars in millions\) \| NORTH AMERICA", text))
        for i, h in enumerate(heads):
            fy = int(h.group(1))
            if fy in done or fy < 2019:
                continue
            done.add(fy)
            end = heads[i + 1].start() if i + 1 < len(heads) else h.start() + 6000
            header = text[h.start(): text.find("Revenues by:", h.start())]
            cols = [SEGMENT_NAMES[c.strip()] for c in header.split("|")[2:]
                    if c.strip() in SEGMENT_NAMES]
            table = f"Revenue disaggregation, year ended May 31, {fy}"
            direct_label = ("Sales through Direct to Consumer"
                            if "Sales through Direct to Consumer" in text[h.start():end]
                            else "Sales through NIKE Direct")
            for measure, label in [("Total revenues", "TOTAL REVENUES"),
                                   ("Sales to wholesale customers", "Sales to Wholesale Customers"),
                                   ("Sales through direct to consumer (NIKE Direct)", direct_label)]:
                vals, pos = row_values(text, h.start(), label, end)
                assert len(vals) >= len(cols), (fy, label, vals)
                for seg, v in zip(cols, vals):
                    record(rows, fy, seg, measure, v, filing_fy, text, pos, table)
    return done


# ---------------------------------------------------------------------------
# STEP 3b: FY2017-FY2018 (before the Revenues note existed)
# ---------------------------------------------------------------------------
# For each year: which 10-K to read, and which column of its 3-year tables
# holds that year. In the "Operating segments" note the columns are just the
# three years (index 0, 1, 2). In the MD&A geography tables each year is
# followed by two "% change" columns, so the oldest year is the 5th number
# (index 4).
OLD_YEARS = {2018: (2020, 2, 4), 2017: (2019, 2, 4)}

SEGMENT_NOTE_ROWS = [("North America", "North America"),
                     ("EMEA", "Europe, Middle East & Africa"),
                     ("Greater China", "Greater China"),
                     ("APLA", "Asia Pacific & Latin America"),
                     ("Global Brand Divisions", "Global Brand Divisions"),
                     ("Total NIKE Brand", "Total NIKE Brand"),
                     ("Converse", "Converse"),
                     ("Corporate", "Corporate"),
                     ("Total NIKE, Inc.", "TOTAL NIKE, INC. REVENUES")]

MDNA_TABLES = [("North America", "NORTH AMERICA"),
               ("EMEA", "EUROPE, MIDDLE EAST & AFRICA"),
               ("Greater China", "GREATER CHINA"),
               ("APLA", "ASIA PACIFIC & LATIN AMERICA"),
               ("Converse", "CONVERSE")]


def from_older_filings(texts, rows):
    for fy, (filing_fy, note_idx, mdna_idx) in OLD_YEARS.items():
        text = texts[filing_fy]
        y0, y1, y2 = filing_fy, filing_fy - 1, filing_fy - 2
        # (i) segment totals, Operating segments note
        start = text.find(f"(Dollars in millions) | {y0} | {y1} | {y2} | REVENUES")
        assert start > 0, f"segment note not found in FY{filing_fy} 10-K"
        for seg, label in SEGMENT_NOTE_ROWS:
            vals, pos = row_values(text, start, label)
            record(rows, fy, seg, "Total revenues", vals[note_idx], filing_fy, text, pos,
                   "Operating segments note: revenues by segment")
        # (ii) wholesale / direct split, per-geography tables in MD&A
        for seg, heading in MDNA_TABLES:
            start = text.find(f"{heading} | (Dollars in millions) | FISCAL {y0}")
            assert start > 0, (heading, filing_fy)
            # the table ends at its EBIT row (capitalised differently by year)
            end = start + text[start:].upper().find("EARNINGS BEFORE INTEREST AND TAXES")
            for measure, labels in [("Sales to wholesale customers", ["Sales to Wholesale Customers"]),
                                    ("Sales through direct to consumer (NIKE Direct)",
                                     ["Sales through NIKE Direct", "Sales through Direct to Consumer"])]:
                for label in labels:
                    try:
                        vals, pos = row_values(text, start, label, end)
                        break
                    except ValueError:
                        vals = None
                if vals is None:      # Converse's channel split isn't in every year's table
                    continue
                record(rows, fy, seg, measure, vals[mdna_idx], filing_fy, text, pos,
                       f"MD&A: {heading.title()} revenue table")
        # (iii) NIKE Brand totals by channel: 'Supplemental NIKE Brand Revenues Details'
        start = text.find("Supplemental NIKE Brand Revenues Details")
        for measure, label in [("Sales to wholesale customers", "Sales to Wholesale Customers"),
                               ("Sales through direct to consumer (NIKE Direct)", "Sales through NIKE Direct")]:
            vals, pos = row_values(text, start, label)
            record(rows, fy, "Total NIKE Brand", measure, vals[mdna_idx], filing_fy, text, pos,
                   "MD&A: Supplemental NIKE Brand Revenues Details")


# ---------------------------------------------------------------------------
# STEP 4: income-statement check (revenue and net income, API vs 10-K)
# ---------------------------------------------------------------------------
def income_statement_check(texts, api):
    """Read Revenues and Net income from the income statement of the FY2026
    and FY2019 10-Ks (three years each) and compare to the SEC API values."""
    out = []
    for filing_fy in (2026, 2019):
        text = texts[filing_fy]
        start = text.find("CONSOLIDATED STATEMENTS OF INCOME | YEAR ENDED MAY 31")
        for item, label, api_col in [("Revenue", "Revenues", "Revenue (USD millions)"),
                                     ("Net income", "NET INCOME", "Net income (USD millions)")]:
            vals, pos = row_values(text, start, label)
            for k, v in enumerate(vals[:3]):
                fy = filing_fy - k
                api_v = round(api.loc[fy, api_col]) if fy in api.index else None
                out.append({"fiscal_year": fy, "item": item,
                            "10k_usd_millions": v, "sec_api_usd_millions": api_v,
                            "difference": None if api_v is None else v - api_v,
                            "source_10k": f"FY{filing_fy} 10-K",
                            "section": "Consolidated Statements of Income",
                            "page": page_at(text, pos), "url": url_for(filing_fy)})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# STEP 5: checks that the pieces add up
# ---------------------------------------------------------------------------
def add_up_checks(long, api):
    """Every check is a row: what was added, what it should equal, difference."""
    tot = long[long.measure == "Total revenues"].pivot(
        index="fiscal_year", columns="segment", values="value_usd_millions")
    checks = []
    geo = ["North America", "EMEA", "Greater China", "APLA", "Global Brand Divisions"]
    for fy, r in tot.iterrows():
        checks.append((fy, "4 geographies + Global Brand Divisions = Total NIKE Brand",
                       r[geo].sum(), r["Total NIKE Brand"]))
        checks.append((fy, "NIKE Brand + Converse + Corporate = Total NIKE, Inc.",
                       r[["Total NIKE Brand", "Converse", "Corporate"]].sum(), r["Total NIKE, Inc."]))
        checks.append((fy, "Total NIKE, Inc. (10-K) = revenue from SEC API",
                       r["Total NIKE, Inc."], round(api.loc[fy, "Revenue (USD millions)"])))
    # wholesale + direct must equal total for each of the four geographies
    w = long.pivot_table(index=["fiscal_year", "segment"], columns="measure",
                         values="value_usd_millions")
    for (fy, seg), r in w.iterrows():
        if seg in geo[:4]:
            checks.append((fy, f"{seg}: wholesale + direct = total",
                           r["Sales to wholesale customers"] + r["Sales through direct to consumer (NIKE Direct)"],
                           r["Total revenues"]))
    c = pd.DataFrame(checks, columns=["fiscal_year", "check", "sum_or_value", "should_equal"])
    c["difference"] = c["sum_or_value"] - c["should_equal"]
    c["ok"] = c["difference"].abs() < 0.5
    return c


def main():
    texts = {fy: load_text(fy) for fy in FILINGS}
    rows = []
    from_revenue_note(texts, rows)
    from_older_filings(texts, rows)
    long = pd.DataFrame(rows).sort_values(["fiscal_year", "segment", "measure"])

    # SEC API figures from 01_download.py, for cross-checking
    wb = sorted(PROCESSED.glob("nike_financials_and_prices_*.xlsx"))[-1]
    api = pd.read_excel(wb, sheet_name="financials_annual", index_col=0)

    # Wide view: one row per year. 'Other' (licensing, hedge results) is NOT
    # printed per channel by Nike, so it is computed and labeled as such.
    wide = long.pivot_table(index="fiscal_year", columns=["measure", "segment"],
                            values="value_usd_millions")
    t = wide["Total revenues"]
    summary = pd.DataFrame({
        "North America revenue (USD m)": t["North America"],
        "EMEA revenue (USD m)": t["EMEA"],
        "Greater China revenue (USD m)": t["Greater China"],
        "APLA revenue (USD m)": t["APLA"],
        "Global Brand Divisions revenue (USD m)": t["Global Brand Divisions"],
        "Total NIKE Brand revenue (USD m)": t["Total NIKE Brand"],
        "Converse revenue (USD m)": t["Converse"],
        "Corporate revenue (USD m)": t["Corporate"],
        "Total NIKE, Inc. revenue (USD m)": t["Total NIKE, Inc."],
        "NIKE Brand wholesale (USD m)": wide["Sales to wholesale customers"]["Total NIKE Brand"],
        "NIKE Brand direct / NIKE Direct (USD m)":
            wide["Sales through direct to consumer (NIKE Direct)"]["Total NIKE Brand"],
    })
    summary["NIKE Direct share of NIKE Brand revenue (%) = direct / Total NIKE Brand"] = (
        100 * summary["NIKE Brand direct / NIKE Direct (USD m)"] / summary["Total NIKE Brand revenue (USD m)"]).round(1)
    summary.index.name = "Fiscal year (ends May 31)"

    checks = add_up_checks(long, api)
    is_check = income_statement_check(texts, api)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    long.to_csv(PROCESSED / "nke_segment_revenue_10k_long.csv", index=False)
    summary.to_csv(PROCESSED / "nke_segment_revenue_10k_summary.csv")
    checks.to_csv(PROCESSED / "nke_segment_revenue_10k_checks.csv", index=False)
    is_check.to_csv(PROCESSED / "check_revenue_net_income_api_vs_10k.csv", index=False)
    with pd.ExcelWriter(PROCESSED / "nke_segment_revenue_10k.xlsx", engine="openpyxl") as xl:
        summary.to_excel(xl, sheet_name="summary")
        long.to_excel(xl, sheet_name="every_number_with_source", index=False)
        checks.to_excel(xl, sheet_name="add_up_checks", index=False)
        is_check.to_excel(xl, sheet_name="income_stmt_check", index=False)

    print(summary.round(0).to_string())
    print(f"\nAdd-up checks: {checks.ok.sum()} of {len(checks)} pass")
    print(checks[~checks.ok].to_string() if (~checks.ok).any() else "")
    print("\nRevenue / net income, 10-K vs SEC API:")
    print(is_check[["fiscal_year", "item", "10k_usd_millions", "sec_api_usd_millions",
                    "difference", "source_10k", "page"]].to_string(index=False))


if __name__ == "__main__":
    main()
