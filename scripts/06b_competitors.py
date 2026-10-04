"""
06b_competitors.py  -  Revenue growth and operating margin for Nike and five competitors

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
Script 06 finds the revenue growth (FY2028-31) and operating margin (by FY2031)
that Nike's share price implies. Is that a lot or a little? Two yardsticks:
Nike's own past (script 06a) and what other sportswear companies earn. This
script builds the second one.

Companies and where the numbers come from:
  Lululemon (USD), Deckers (USD)  - SEC 10-K filings, via the SEC XBRL company facts API
  On Holding (CHF)                - SEC 20-F filings (IFRS), via the same API
  adidas, Puma (EUR)              - NOT SEC filers. Read from each company's 2025 annual
                                    report ten-year table, downloaded 2026-10-04 into
                                    data/raw/competitors/ (adidas: report.adidas-group.com,
                                    Puma: annual-report.puma.com). Labelled NON-SEC.
  Nike                            - output/06a_nike_history_fy1993_fy2026.csv (SEC)

Margins are computed as operating income / revenue, each in the company's own
currency, so currency does not matter. Growth is nominal and in the company's own
currency (so adidas and Puma growth includes no USD/EUR effect), the same basis
as Nike's USD growth. Multi-year growth is compound annual growth (the same
definition script 06 uses for Nike's "normal" growth); margins are simple averages.

Lining up different fiscal years: each company's year is labelled by the calendar
year most of it falls in. Nike's FY2026 (June 2025 - May 2026) is labelled 2025;
Lululemon's fiscal 2025 (ends 1 Feb 2026) is 2025; Deckers' fiscal 2026 (ends 31
March 2026) is 2025.

Every company is on the same "as reported" basis: operating income including
one-off charges (e.g. Puma 2025 includes EUR 191.6m of one-offs). For Nike that
is script 06a's "operating income incl. one-offs" (gross profit - S&A - any one-off
lines shown separately below S&A); in 2015-2025 Nike had no separate lines, so it
equals the gross profit - S&A figure the DCF uses.

Outputs
  output/06b_competitors_by_year.csv   one row per company and year, with source
  output/06b_competitors_summary.csv   averages and ranges per company
  charts/06b_margin_and_growth_vs_peers.png
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/competitors"
NIKE_HISTORY = ROOT / "output/06a_nike_history_fy1993_fy2026.csv"
HEADLINE = ROOT / "output/06_headline_result.csv"     # from 06_implied_growth_and_margin.py
FIRST_YEAR, LAST_YEAR = 2016, 2025                     # calendar-year labels shown

SEC_FILERS = {
    # name: (company facts file, XBRL namespace, revenue tags in order of preference, operating income tag, currency)
    "Lululemon": ("companyfacts_CIK0001397187_lululemon_2026-10-04.json", "us-gaap",
                  ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"], "OperatingIncomeLoss", "USD"),
    "Deckers": ("companyfacts_CIK0000910521_deckers_2026-10-04.json", "us-gaap",
                ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueGoodsNet"], "OperatingIncomeLoss", "USD"),
    "On Holding": ("companyfacts_CIK0001858985_on_holding_2026-10-04.json", "ifrs-full",
                   ["RevenueFromContractsWithCustomers"], "ProfitLossFromOperatingActivities", "CHF"),
}


def label_year(end):
    """Calendar year most of the fiscal year falls in: a year ending Jan-Jun belongs mostly to the year before."""
    end = pd.Timestamp(end)
    return end.year if end.month >= 7 else end.year - 1


def annual_values(facts, tags, currency):
    """Full-year values from annual filings (10-K / 20-F); the most recent filing wins for each year."""
    out = {}
    for tag in tags:
        for x in facts.get(tag, {}).get("units", {}).get(currency, []):
            if x.get("form") not in ("10-K", "20-F") or "start" not in x:
                continue
            if not 350 <= (pd.Timestamp(x["end"]) - pd.Timestamp(x["start"])).days <= 380:
                continue
            y = label_year(x["end"])
            if y not in out or x["filed"] > out[y]["filed"]:
                out[y] = {"value": x["val"] / 1e6, "filed": x["filed"], "accn": x["accn"], "form": x["form"],
                          "end": x["end"], "tag": tag}
    return out


# ---------------------------------------------------------------------------
# STEP 1. SEC filers (Lululemon, Deckers, On)
# ---------------------------------------------------------------------------
rows = []
for name, (fname, ns, rev_tags, oi_tag, cur) in SEC_FILERS.items():
    facts = json.loads((RAW / fname).read_text())["facts"][ns]
    rev = {}
    for tag in reversed(rev_tags):              # later tags in the list are older; preferred tag overwrites
        rev.update(annual_values(facts, [tag], cur))
    oi = annual_values(facts, [oi_tag], cur)
    for y in sorted(set(rev) & set(oi)):
        rows.append({"company": name, "year": y, "fiscal_year_end": rev[y]["end"], "currency": cur,
                     "revenue_m": rev[y]["value"], "operating_income_m": oi[y]["value"],
                     "source": f"SEC {rev[y]['form']} accession {rev[y]['accn']} filed {rev[y]['filed']} (XBRL company facts)"})

# ---------------------------------------------------------------------------
# STEP 2. adidas and Puma (non-SEC annual reports, typed in with sources)
# ---------------------------------------------------------------------------
ADIDAS_HTML = RAW / "adidas_AR2025_ten_year_overview_2026-10-04.html"
ADIDAS_URL = "https://report.adidas-group.com/2025/en/additional-information/ten-year-overview.html"
PUMA_HTML = RAW / "puma_AR2025_group_development_2026-10-04.html"
PUMA_URL = "https://annual-report.puma.com/2025/en/additional-information/puma-group-development/index.html"


def eur_number(text, german):
    """Turn a table cell into a number.
    adidas (english style): '24,811', negatives in brackets '(58)'.
    Puma (german style): '7.296,2', but '548.7' below 1,000, and '–357,2' for negatives."""
    t = str(text).strip().replace("–", "-").replace("\u2212", "-")
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if not german:
        t = t.replace(",", "")        # comma only groups thousands
    elif "," in t:                    # '.' groups thousands, ',' is the decimal point
        t = t.replace(".", "").replace(",", ".")
    return -float(t) if neg else float(t)


def year_of(header):
    """Year headers carry footnote digits stuck on the end, e.g. '20181' = 2018 + footnote 1."""
    return int(str(header).strip()[:4])


def read_ten_year(path, url, company, sales_label, profit_label, german, year_row=None, note=""):
    t = pd.read_html(path, thousands=None)[0].astype(str)
    if year_row is not None:                         # Puma: years are in the first row, not the header
        t.columns = t.iloc[year_row]
    labels = t.iloc[:, 0].str.strip()
    sales = t[labels.str.match(sales_label)].iloc[0]
    profit = t[labels.str.match(profit_label)].iloc[0]
    out = []
    for col in t.columns[1:]:
        if not str(col)[:4].isdigit() or sales[col] in ("nan", ""):
            continue
        y = year_of(col)
        out.append({"company": company, "year": y, "fiscal_year_end": f"{y}-12-31", "currency": "EUR",
                    "revenue_m": eur_number(sales[col], german), "operating_income_m": eur_number(profit[col], german),
                    "source": f"NON-SEC: {company} Annual Report 2025, {url} (saved as data/raw/competitors/{path.name}){note}"})
    return out


# adidas: 2016-2019 exclude TaylorMade and other golf/hockey brands sold since; 2020-2025 also
# exclude Reebok (sold 2022). So 2019 still includes Reebok and 2020 does not (footnotes 3 and 4).
rows += read_ten_year(ADIDAS_HTML, ADIDAS_URL, "adidas", r"Net sales", r"Operating profit", german=False,
                      note="; continuing operations: 2016-19 incl. Reebok, 2020-25 excl. Reebok (footnotes 3-4)")
# Puma: 2024 includes adjustments for the discontinued PUMA United business (footnote 1).
rows += read_ten_year(PUMA_HTML, PUMA_URL, "Puma", r"Consolidated sales", r"Operating result \(EBIT\)", german=True, year_row=0,
                      note="; reported EBIT incl. one-offs; 2024 adjusted for discontinued PUMA United (footnote 1)")

# ---------------------------------------------------------------------------
# STEP 3. Nike, from script 06a
# ---------------------------------------------------------------------------
nike = pd.read_csv(NIKE_HISTORY)
for _, r in nike.iterrows():
    rows.append({"company": "Nike", "year": int(r["fiscal_year"]) - 1, "fiscal_year_end": f"{int(r['fiscal_year'])}-05-31",
                 "currency": "USD", "revenue_m": r["revenue_usd_m"], "operating_income_m": r["operating_income_incl_one_offs_usd_m"],
                 "source": r["source"]})

# ---------------------------------------------------------------------------
# STEP 4. Growth and margin, then a summary per company
# ---------------------------------------------------------------------------
df = pd.DataFrame(rows).sort_values(["company", "year"]).reset_index(drop=True)
df["revenue_growth_pct"] = df.groupby("company")["revenue_m"].pct_change() * 100
df.loc[df.groupby("company")["year"].diff() != 1, "revenue_growth_pct"] = float("nan")   # only year-on-year
# adidas 2020 vs 2019 compares sales without Reebok to sales with it, so it is not a real growth rate.
df.loc[(df["company"] == "adidas") & (df["year"] == 2020), "revenue_growth_pct"] = float("nan")
df["operating_margin_pct"] = df["operating_income_m"] / df["revenue_m"] * 100
df = df[df["year"].between(FIRST_YEAR - 1, LAST_YEAR)]
df.rename(columns={"year": "calendar_year_label"}).round(2).to_csv(ROOT / "output/06b_competitors_by_year.csv", index=False)

shown = df[df["year"].between(FIRST_YEAR, LAST_YEAR)]
def cagr(g, first, last):
    """Compound annual revenue growth from year `first` to year `last` (%), or NaN if a year is missing."""
    r = g.set_index("year")["revenue_m"]
    if first not in r or last not in r:
        return float("nan")
    return ((r[last] / r[first]) ** (1 / (last - first)) - 1) * 100


summary = []
for c, g in df.groupby("company"):
    w = g[g["year"].between(FIRST_YEAR, LAST_YEAR)]
    summary.append({
        "company": c, "currency": g["currency"].iloc[0], "years_available": f"{w['year'].min()}-{w['year'].max()}",
        "growth_cagr_2016_to_2019_pct": cagr(g, 2016, 2019), "growth_cagr_2021_to_2025_pct": cagr(g, 2021, 2025),
        "avg_margin_2016_19_pct": w[w["year"].between(2016, 2019)]["operating_margin_pct"].mean(),
        "avg_margin_2022_25_pct": w[w["year"].between(2022, 2025)]["operating_margin_pct"].mean(),
        "latest_year": w["year"].max(), "latest_growth_pct": w["revenue_growth_pct"].iloc[-1],
        "latest_margin_pct": w["operating_margin_pct"].iloc[-1],
        "min_margin_pct": w["operating_margin_pct"].min(), "max_margin_pct": w["operating_margin_pct"].max(),
        "sec_filer": "no (NON-SEC annual report)" if c in ("adidas", "Puma") else "yes",
    })
summary = pd.DataFrame(summary).round(1)
summary.to_csv(ROOT / "output/06b_competitors_summary.csv", index=False)
print(summary.to_string(index=False))

# ---------------------------------------------------------------------------
# STEP 5. Chart: margin (top) and growth (bottom), Nike drawn heavier, with the
# price-implied margin and growth from script 06 as dashed lines
# ---------------------------------------------------------------------------
head = pd.read_csv(HEADLINE, index_col="item")["value"]
imp_g = head["implied revenue growth per year FY2028-31"] * 100
imp_m = head["implied operating margin by FY2031"] * 100

order = ["Nike", "adidas", "Puma", "Lululemon", "Deckers", "On Holding"]
colors = ["#0b0b0b", "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
fig, axes = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
for metric, ax, implied_value, label, note in [
        ("operating_margin_pct", axes[0], imp_m, "Operating margin (%)", "margin by FY2031"),
        ("revenue_growth_pct", axes[1], imp_g, "Revenue growth (%, own currency)", "growth a year,\nFY2028-31")]:
    for c, col in zip(order, colors):
        g = shown[shown["company"] == c]
        ax.plot(g["year"], g[metric], color=col, lw=3 if c == "Nike" else 2, marker="o", ms=5 if c != "Nike" else 7,
                label=c + (" (non-SEC)" if c in ("adidas", "Puma") else ""), zorder=3 if c == "Nike" else 2)
    ax.hlines(implied_value, FIRST_YEAR - 0.4, LAST_YEAR + 0.2, color="#0b0b0b", ls="--", lw=1.5)
    # The label sits to the right of the last year, so it never covers a company's line.
    ax.text(LAST_YEAR + 0.25, implied_value, f"Nike's price\nimplies {implied_value:.1f}%\n{note}", va="center",
            fontsize=9, fontweight="bold")
    ax.set_xlim(FIRST_YEAR - 0.4, LAST_YEAR + 1.6)
    ax.axhline(0, color="#999999", lw=0.8)
    ax.set_ylabel(label)
    ax.grid(axis="y", color="#e5e5e5")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
axes[0].legend(ncol=3, fontsize=9, loc="upper left", bbox_to_anchor=(0, 1.22), frameon=False)
axes[1].set_xticks(range(FIRST_YEAR, LAST_YEAR + 1))
axes[1].set_xlabel("Year (calendar year most of each company's fiscal year falls in; Nike FY2026 = 2025)")
fig.suptitle("Nike vs peers: operating margin and revenue growth", x=0.06, ha="left", fontsize=13, fontweight="bold")
fig.tight_layout()
fig.savefig(ROOT / "charts/06b_margin_and_growth_vs_peers.png", dpi=150)
print("Saved output/06b_*.csv and charts/06b_margin_and_growth_vs_peers.png")
