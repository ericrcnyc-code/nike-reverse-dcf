# What is the market pricing into Nike?

**A reverse DCF of Nike (NYSE: NKE), built from Nike's own SEC filings.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)
![Data: SEC EDGAR](https://img.shields.io/badge/data-SEC%20EDGAR-1f4e79)
![Audit: 256 checks passed](https://img.shields.io/badge/data%20audit-256%20checks%20passed-2e8540)
![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)

A discounted cash flow (DCF) model usually runs forward: forecast a company's cash flows, discount them, and get a value
per share. A **reverse DCF** runs backwards. It starts from today's share price and solves for the revenue growth and
profit margin that would make that price fair. This project asks one question:

> **At $33.87 a share (close on 2 October 2026), what future is the market assuming for Nike?**

**Short answer:** after the weak year Nike itself guides to for FY2027, the price assumes revenue growth of about
**2.9% a year** in FY2028-31 and an operating margin back to about **10.3% by FY2031**. That is roughly halfway back to
the Nike of FY2017-24, which grew 5.9% a year at a 12.5% margin.

*A personal learning project in financial modeling. Not investment advice.*

![What growth does Nike's share price imply?](charts/04_implied_growth_by_margin.png)

## Contents

- [Headline findings](#headline-findings)
- [Method, step by step](#method-step-by-step)
- [Data sources](#data-sources)
- [How to run it](#how-to-run-it)
- [Repository layout](#repository-layout)
- [Limits](#limits)

**Full results:** [`output/00_nike_valuation_summary.md`](output/00_nike_valuation_summary.md) ·
**Excel model:** [`output/05_nike_dcf_model.xlsx`](output/05_nike_dcf_model.xlsx) ·
**Every assumption:** [`scripts/assumptions.py`](scripts/assumptions.py)

## Headline findings

All figures are nominal. Valuation date 2026-10-02; data as of 2026-10-04.

| Question | Answer |
|---|---|
| What does the $33.87 price assume? | After FY2027 at Nike's guidance (revenue down about 8%, adjusted operating margin about 5.6%), revenue growth of about **2.9% a year** in FY2028-31 and an operating margin of about **10.3% by FY2031** |
| How does that compare with Nike's past? | About 48% of the way back from FY2026 (0.2% growth, 8.2% margin) to Nike's FY2017-24 average (5.9% growth, 12.5% margin) |
| What is Nike worth in the base case? | **$42.17 a share**, 25% above the price, if the margin recovers to 12.5% by FY2031 |
| What would a full recovery be worth? | About $45 a share |
| Value with every harsher input at once | $33.58, about 1% below the price |
| How does Nike trade against peers? | 11.0x EV/EBITDA and 16.3x P/E, against a peer median of 8.8x and 14.5x |

**What drives the answer.** The price mostly pins down the *margin*, not growth. Each point of FY2031 operating margin
is worth about $3-4 a share, while moving growth from 0% to 6% at a 12.5% margin only lifts the value from $37 to $45.
Whatever growth you believe, the market is pricing a margin of roughly 10%.

**How to read it** (interpretation, not a model output): the market prices a partial recovery. A 10% margin is below
Nike's FY2017-24 record and weaker than its recovery after its last brand-driven slump in FY1998-99, but well above
the 5.6% Nike guides to for FY2027.

<table>
<tr>
<td width="50%"><img src="charts/06_value_heatmap_growth_x_margin.png" alt="Value per share by growth and margin"></td>
<td width="50%"><img src="charts/06b_margin_and_growth_vs_peers.png" alt="Nike vs peers: margin and growth"></td>
</tr>
<tr>
<td><b>Value per share for every growth and margin pair.</b> Red cells are worth less than the price, blue more; the black line is every pair worth exactly $33.87.</td>
<td><b>Nike against peers.</b> The price-implied 10.3% margin sits between the big European brands (adidas, Puma) and the focused growers (Lululemon, Deckers).</td>
</tr>
</table>

## Method, step by step

1. **Collect the data** (scripts 01, 01b). Nike's financials for FY2017-FY2026 come from the SEC's XBRL "company
   facts" API, and segment and channel revenue is read straight out of each 10-K. Daily share prices come from Yahoo
   Finance. Every number keeps a receipt: form, accession number and filing date.
2. **Describe what happened** (script 02). Revenue, margins, free cash flow and return on capital over ten years,
   plus segment and channel trends and charts. Nike reports no operating income line, so operating income here is
   gross profit minus selling and administrative expense.
3. **Estimate the discount rate** (scripts 03, 04). Beta from 60 monthly returns against the S&P 500, the 10-year
   Treasury yield, and Damodaran's implied equity risk premium give a cost of equity of 9.74% and a WACC of 9.07%.
4. **Build one DCF** ([`scripts/dcf_model.py`](scripts/dcf_model.py)). Five forecast years (FY2027-31). FY2027 is fixed
   at Nike's guidance; after that the margin moves in a straight line to its target. Taxes, depreciation, capital
   spending and working capital are percentages of revenue taken from Nike's FY2017-26 averages. The terminal value
   treats FY2032 as a normal year growing 2.5% forever. Value per share = (enterprise value + cash - debt) / diluted
   shares, with cash, debt and shares from the Q1 FY2027 10-Q.
5. **Run it backwards** (scripts 04, 06). Solve for the growth rate that makes the DCF value equal the share price,
   for a range of margins, since one price cannot pin down two unknowns at once.
6. **Build the same model in Excel** (script 05). The workbook uses live formulas, and script 06 checks that Excel and
   Python agree to the cent.
7. **Put it in context** (scripts 06a, 06b, 08). Nike's own history back to FY1993, competitors' growth and margins,
   and valuation multiples against adidas, Lululemon, Deckers, On Holding and Under Armour.
8. **Stress-test it** (script 07). Change one input at a time (risk premium, terminal growth, tax, working capital,
   leases), then all the harsher ones together.
9. **Audit the data** (script 09). 256 checks: 220 Nike figures found next to their labels in the 10-K text, 13
   against the 10-Q, 11 market inputs against the raw downloads, and 8 checks that scripts agree with each other.
   No failures.
10. **Scenarios** (script 10). Bear ($23.90), cautious base ($35.53) and bull ($44.65) values built from Nike's FY2027
    guidance.

Three rules run through the whole project: official SEC filings are the source of truth for financials; every modeling
assumption lives in one file with its source and date; and every intermediate calculation is saved as a CSV so it can
be checked by hand. How the model changed while it was built is in the [changelog](CHANGELOG.md).

## Data sources

| Data | Source | In this repository? |
|---|---|---|
| Nike financials, FY2017-FY2026 | SEC EDGAR XBRL company facts API | Yes (`data/raw/`) |
| Nike 10-Ks FY2017-26, six older 10-Ks (1995-2009), Q1 FY2027 10-Q, 8-K of 2026-10-01 | SEC EDGAR | Yes (`data/raw/10k/`, `10k_history/`, `10q/`, `8k/`) |
| Lululemon, Deckers, On Holding, Under Armour financials | SEC EDGAR | Yes (`data/raw/competitors/`) |
| Share prices, S&P 500, 10-year Treasury yield, exchange rates | Yahoo Finance via `yfinance` | Yes (small CSVs in `data/raw/`) |
| Equity risk premium (`ERPbymonth.xlsx`) | Aswath Damodaran, NYU Stern | No: run `scripts/00_get_non_sec_files.py` |
| adidas 2025 annual report pages and 2025/2026 half-year reports | adidas | No: same script |
| Puma 2025 annual report page | Puma | No: same script |

SEC filings are public. The Damodaran, adidas and Puma files belong to their publishers, so the repository links to
them instead of copying them; `00_get_non_sec_files.py` downloads each one to the file name the scripts expect.
On 2026-10-04 every file it downloaded was byte-for-byte identical to the copy used for the results.

## How to run it

### 1. Set up (once)

You need Python 3.11 or newer, plus two system programs: **LibreOffice Calc** (script 05 uses it to recalculate the
Excel formulas) and **pdftotext** (script 08 uses it to read the adidas half-year PDFs).

```bash
git clone https://github.com/ericrcnyc-code/nike-reverse-dcf.git
cd nike-reverse-dcf

python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Linux (Debian/Ubuntu):
sudo apt-get install libreoffice-calc poppler-utils
# macOS (Homebrew):
brew install --cask libreoffice && brew install poppler
```

The SEC asks every program that downloads from it to identify itself with a name and contact email. The scripts use a
generic name; to use your own, set it before running the download scripts:

```bash
export SEC_USER_AGENT="your-name your-email@example.com"
```

### 2. Get the non-SEC files

```bash
python3 scripts/00_get_non_sec_files.py
```

### 3. Run the scripts in order

All commands run from the repository's top folder.

```bash
python3 scripts/02_historical_metrics.py
python3 scripts/04_reverse_dcf.py
python3 scripts/05_excel_dcf_model.py
python3 scripts/06a_nike_long_history.py
python3 scripts/06_implied_growth_and_margin.py
python3 scripts/06b_competitors.py
python3 scripts/07_valuation_risk_checks.py
python3 scripts/08_peer_multiples.py
python3 scripts/09_data_audit.py
python3 scripts/10_memo_scenarios.py
```

This rebuilds everything in `output/` and `charts/` from the saved raw data. A fresh clone rebuilds every output CSV
unchanged and the audit passes all 256 checks (the PNG and Excel files differ only in their embedded timestamps).

Scripts **01, 01b and 03 download fresh data** (SEC filings and today's prices). They are not needed to reproduce the
results above. Run them only when you want to update the analysis, and then copy the new market figures that script 03
prints into `scripts/assumptions.py` by hand, with the date, before running the rest.

| Script | What it does |
|---|---|
| `00_get_non_sec_files.py` | Downloads the Damodaran, adidas and Puma files |
| `01_download.py` | Nike financials from the SEC and prices from Yahoo, into one workbook in `data/processed/` |
| `01b_segments_from_10k.py` | Segment and channel revenue read from each 10-K |
| `02_historical_metrics.py` | Historical metrics, segment trends, charts |
| `03_market_inputs.py` | Prices, Treasury yield and beta |
| `04_reverse_dcf.py` | WACC, latest balance sheet, and the reverse DCF |
| `05_excel_dcf_model.py` | The Excel DCF workbook with live formulas |
| `06a_nike_long_history.py` | Nike's growth and margins back to FY1993 |
| `06_implied_growth_and_margin.py` | Implied growth for each margin, and the value heatmap |
| `06b_competitors.py` | Competitors' growth and margins |
| `07_valuation_risk_checks.py` | Sensitivity of the value to each input |
| `08_peer_multiples.py` | EV/EBITDA and P/E against peers |
| `09_data_audit.py` | Checks every key number against the filings; stops on any failure |
| `10_memo_scenarios.py` | Bear, base and bull scenarios |
| `assumptions.py` | Every modeling assumption, with source and date |
| `dcf_model.py` | The one DCF that the other scripts use |

Each script opens with a plain-language explanation of what it does and why.

## Repository layout

```
nike-reverse-dcf/
├── scripts/          Python code, numbered in run order; assumptions.py and dcf_model.py
├── data/
│   ├── raw/          files exactly as downloaded, never edited
│   └── processed/    clean tables the scripts build from the raw files
├── output/           results, every intermediate calculation (CSV), Excel models, write-ups
├── charts/           charts (PNG), each made by a script
├── CHANGELOG.md      how the model and its results changed while it was built
└── requirements.txt  Python libraries
```

The write-ups in `output/` explain each step in plain language; [`output/README.md`](output/README.md) lists every file.

## Limits

- **FY2027 comes from Nike's guidance**, not an independent forecast. The 5.55% margin is an adjusted figure (before
  restructuring charges) and rests on reading "high-single digit" decline as -8% and a "mid-20s" tax rate as 25%.
- The base case's growth path and 12.5% margin target are judgment, and they drive its value more than any other
  input. The reverse DCF avoids them by asking what the price implies instead.
- Terminal value is 77% of enterprise value, so the long run dominates the answer.
- adidas and Puma figures come from their annual reports, not the SEC. Peer figures were not re-checked line by line
  against the printed filings the way Nike's were.
- Shares are diluted weighted-average shares, because the SEC data has no period-end count after 2015. The difference
  is under 1%.
- Nike's figures before FY2008 were not restated for later acquisitions and sales, so growth in those years includes
  some acquisition effect.

## License

Code is released under the [MIT License](LICENSE). Filings and market data belong to their publishers (the SEC
filings are public records).
