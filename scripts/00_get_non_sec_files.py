"""
00_get_non_sec_files.py  -  Download the non-SEC source files that are not stored in the repository

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
Most raw data in this project is official SEC data (public, and kept in the
repository under data/raw/). A few inputs come from other publishers:
  - Professor Aswath Damodaran's monthly equity risk premium file (NYU Stern)
  - adidas's 2025 annual report pages and its 2025 and 2026 half-year reports
  - Puma's 2025 annual report page
Those belong to their publishers, so the repository does not copy them. This
script downloads each one from its original web address and saves it under the
exact file name the other scripts expect (the names carry the date they were
first saved, 2026-10-04, so the scripts and the audit trail stay unchanged).

A file that is already on disk is skipped, so running it twice is harmless.

WHICH SCRIPTS NEED THESE FILES
------------------------------
  06b_competitors.py    adidas ten-year overview, Puma group development
  08_peer_multiples.py  adidas statements, notes and half-year reports
  09_data_audit.py      Damodaran's ERPbymonth.xlsx
Scripts 01-06 and 07 run without them.

A CAUTION
---------
Publishers update their files. Damodaran adds a row every month, which is fine
(the audit looks up the 2026-09-01 row). If adidas or Puma ever change a page,
the numbers read from it could change too; scripts 06b and 08 check their
results against each other and stop if the adidas figures disagree.

HOW TO RUN
----------
    python3 scripts/00_get_non_sec_files.py
Needs: requests.
"""

from pathlib import Path

import requests

# Folder locations. PROJECT is the folder that holds data/, scripts/, output/.
PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"

# Some of these sites refuse requests that don't look like a web browser.
HEADERS = {"User-Agent": "Mozilla/5.0 (nike-valuation-project personal-research)"}

ADIDAS_AR = "https://report.adidas-group.com/2025/en"
ADIDAS_NOTES = f"{ADIDAS_AR}/consolidated-financial-statements/notes"
ADIDAS_H1 = "https://res.cloudinary.com/confirmed-web/image/upload"

# (where to save it, under data/raw/)  ->  (where it comes from)
FILES = {
    "damodaran/ERPbymonth.xlsx":
        "https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx",
    "competitors/adidas_AR2025_ten_year_overview_2026-10-04.html":
        f"{ADIDAS_AR}/additional-information/ten-year-overview.html",
    "competitors/adidas_AR2025_consolidated_income_statement_2026-10-04.html":
        f"{ADIDAS_AR}/consolidated-financial-statements/consolidated-income-statement.html",
    "competitors/adidas_AR2025_consolidated_statement_of_cash_flows_2026-10-04.html":
        f"{ADIDAS_AR}/consolidated-financial-statements/consolidated-statement-of-cash-flows.html",
    "competitors/adidas_AR2025_consolidated_statement_of_financial_position_2026-10-04.html":
        f"{ADIDAS_AR}/consolidated-financial-statements/consolidated-statement-of-financial-position.html",
    "competitors/adidas_AR2025_note_earnings_per_share_2026-10-04.html":
        f"{ADIDAS_NOTES}/notes-to-the-consolidated-income-statement/earnings-per-share.html",
    "competitors/adidas_AR2025_note_financial_income_financial_expenses_2026-10-04.html":
        f"{ADIDAS_NOTES}/notes-to-the-consolidated-income-statement/financial-income-financial-expenses.html",
    "competitors/adidas_AR2025_note_lease_liabilities_2026-10-04.html":
        f"{ADIDAS_NOTES}/notes-to-the-consolidated-statement-of-financial-position/lease-liabilities.html",
    "competitors/adidas_AR2025_note_right_of_use_assets_2026-10-04.html":
        f"{ADIDAS_NOTES}/notes-to-the-consolidated-statement-of-financial-position/right-of-use-assets.html",
    "competitors/adidas_H1_Report_2026_EN_2026-10-04.pdf":
        f"{ADIDAS_H1}/v1785388904/adidas-group/investors/financial-publications/2026/Q2/EN/H1_Report_2026_en_emhpcd.pdf",
    "competitors/adidas_H1_Report_2025_EN_2026-10-04.pdf":
        f"{ADIDAS_H1}/v1753852841/adidas-group/investors/financial-publications/2025/Q2/H1_2025_Report_EN_Final_xvs0k3.pdf",
    "competitors/puma_AR2025_group_development_2026-10-04.html":
        "https://annual-report.puma.com/2025/en/additional-information/puma-group-development/index.html",
}

for name, url in FILES.items():
    path = RAW / name
    if path.exists():
        print(f"already have  {name}")
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()          # stop loudly if a page has moved
    path.write_bytes(resp.content)   # saved exactly as downloaded
    print(f"downloaded    {name}  ({len(resp.content) / 1024:,.0f} KB)  from {url}")
