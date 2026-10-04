"""
06_implied_growth_and_margin.py  -  What growth and margin is Nike's share price assuming?

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
The Excel model (output/05_nike_dcf_model.xlsx) goes forward: we pick revenue
growth and an operating margin, and it gives a value per share. This script runs
the SAME model backwards: we fix the value at today's share price ($33.87) and
ask which growth and margin produce it.

"The same model" is literal: the DCF lives in scripts/dcf_model.py, shared by
scripts 04, 05 (which writes the same formulas into Excel) and this one. Step 1
proves the Excel workbook and dcf_model.py give the same value to the cent.

The catch: the price is ONE number but we have TWO unknowns (growth and margin).
Many pairs give exactly $33.87: lower margin with faster growth, or higher margin
with slower growth. So the script does three things:

  1. Iso-price curve. For each margin in a list (6%, 7%, ... 16%), it finds the one
     growth rate that makes the model value equal the price. Plotted, these pairs
     form a line: every point on it is "a story the market price is consistent with".
  2. Headline pair. To pick ONE point, it asks: if Nike recovers the SAME share of
     the way back to its normal record on both growth and margin, how far back
     must it get? "Normal" = FY2017-FY2024: compound annual revenue growth
     (FY2016 to FY2024) and the simple average operating margin. The starting point
     is FY2026. FY2027 itself is fixed at Nike's guidance (-8% revenue, ~5.6% margin)
     in every run, so the growth found here is for FY2028-FY2031. This is a judgment call about which point to headline, not
     something the price tells us.
  3. Heatmap. Value per share for a grid of growth rates x margins, with the
     $33.87 line drawn on it.

HOW THE SOLVER WORKS (bisection, dcf_model.bisect)
--------------------------------------------------
For a given margin, a higher growth rate gives a higher value per share. So we
can trap the answer: start with a growth rate that is clearly too low (-20%, value
below the price) and one clearly too high (+40%, value above). Try the midpoint.
If its value is above the price, the answer is in the lower half, otherwise the
upper half. Throw away the wrong half and repeat. Each round halves the gap; it
stops when the value is within $0.001 of the price. It is the same thing as
Excel's Goal Seek, written out so every step is visible.

All growth rates and money amounts are nominal (not adjusted for inflation), the
same as the discount rate (the 10-year Treasury yield is a nominal rate).

Outputs (all in output/ unless noted)
  06_base_case_check.csv                  Excel value vs dcf_model.py value (must match)
  06_iso_price_curve.csv                  for each margin: the growth that gives $33.87 (+ the FY2030 variant)
  06_headline_result.csv                  the headline pair and the full-recovery value
  06_headline_forecast.csv                year-by-year forecast at the headline pair (check it by hand)
  06_sensitivity_value_per_share_usd.csv  the heatmap's numbers
  06_history_reference.csv                Nike's FY2017-24 "normal" and FY2026 starting point
  charts/06_value_heatmap_growth_x_margin.png
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assumptions as A
import dcf_model as D

ROOT = Path(__file__).resolve().parent.parent
MODEL_XLSX = ROOT / "output/05_nike_dcf_model.xlsx"
HISTORY_CSV = ROOT / "output/06a_nike_history_fy1993_fy2026.csv"   # from 06a_nike_long_history.py
OUT = ROOT / "output"
CHART = ROOT / "charts/06_value_heatmap_growth_x_margin.png"
PRICE = A.SHARE_PRICE["value"]

# ---------------------------------------------------------------------------
# STEP 1. Check: the Excel workbook and dcf_model.py must agree
# ---------------------------------------------------------------------------
wb = load_workbook(MODEL_XLSX, data_only=True)       # data_only = the computed numbers, not formulas


def named(name):
    """Value of a named cell in the workbook, e.g. named('Value_Per_Share')."""
    sheet, ref = next(iter(wb.defined_names[name].destinations))
    return wb[sheet][ref.replace("$", "")].value


checks = pd.DataFrame([
    {"item": "WACC", "excel": named("WACC"), "dcf_model_py": D.WACC},
    {"item": "Value per share, base case (USD)", "excel": named("Value_Per_Share"),
     "dcf_model_py": D.value_per_share(D.base_case_growth())},
])
checks["difference"] = checks["dcf_model_py"] - checks["excel"]
checks.to_csv(OUT / "06_base_case_check.csv", index=False)
assert (checks["difference"].abs() < 1e-6).all(), f"Excel and dcf_model.py disagree:\n{checks}"
print(f"Check passed: Excel and dcf_model.py both give ${checks['excel'].iloc[1]:.4f} in the base case")

# ---------------------------------------------------------------------------
# STEP 2. Iso-price curve: for each margin, the growth that gives the share price
# ---------------------------------------------------------------------------
curve = []
for m in A.IMPLIED_MARGIN_GRID["value"]:
    g, rounds = D.implied_growth(m)
    g30, _ = D.implied_growth(m, years_to_target=A.YEARS_TO_REACH_TARGET_MARGIN["value"] - 1)
    curve.append({"operating_margin_by_fy2031": m, "implied_growth_per_year_fy2028_31": g,
                  "value_check_usd": D.value_per_share(D.constant(g), m) if g == g else np.nan,
                  "bisection_rounds": rounds,
                  "implied_growth_if_margin_reached_by_fy2030": g30})
curve = pd.DataFrame(curve)
curve.to_csv(OUT / "06_iso_price_curve.csv", index=False)
print("\nIso-price curve (growth per year that gives the share price):")
print(curve.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# ---------------------------------------------------------------------------
# STEP 3. History reference points and the headline pair
# ---------------------------------------------------------------------------
hist = pd.read_csv(HISTORY_CSV, index_col="fiscal_year")
y0, y1 = A.HISTORY_REFERENCE_YEARS["value"]
n_years = y1 - y0 + 1
# Compound annual growth: the one constant rate that takes FY2016 revenue to FY2024 revenue.
normal_g = (hist.loc[y1, "revenue_usd_m"] / hist.loc[y0 - 1, "revenue_usd_m"]) ** (1 / n_years) - 1
normal_m = hist.loc[y0:y1, "operating_margin_pct"].mean() / 100
base = D.base_year()
start_g = hist.loc[D.BASE_FY, "revenue_growth_pct"] / 100
start_m = base["margin"]
pd.DataFrame([
    {"point": f"Normal Nike: FY{y0}-FY{y1}", "revenue_growth": normal_g, "operating_margin": normal_m,
     "how": f"growth = compound annual growth FY{y0 - 1} to FY{y1} revenue; margin = simple average of the {n_years} years"},
    {"point": f"Starting point: FY{D.BASE_FY} actual", "revenue_growth": start_g, "operating_margin": start_m,
     "how": "10-K FY2026"},
]).to_csv(OUT / "06_history_reference.csv", index=False)


def at_recovery(s):
    """Growth and margin when Nike gets share s (0 = stays at FY2026, 1 = fully back to normal) of the way back."""
    return start_g + s * (normal_g - start_g), start_m + s * (normal_m - start_m)


s_star, _ = D.bisect(lambda s: D.value_per_share(D.constant(at_recovery(s)[0]), at_recovery(s)[1]) - PRICE, -1.0, 1.0)
head_g, head_m = at_recovery(s_star)
head_value, head_table, head_summary = D.run(D.constant(head_g), head_m)
head_table.to_csv(OUT / "06_headline_forecast.csv", index=False)
full_value = D.value_per_share(D.constant(normal_g), normal_m)
pd.DataFrame([
    {"item": "share of the way back to normal (0 = FY2026, 1 = normal)", "value": s_star},
    {"item": "implied revenue growth per year FY2028-31", "value": head_g},
    {"item": "implied operating margin by FY2031", "value": head_m},
    {"item": "value per share at the pair (USD; = price)", "value": head_value},
    {"item": f"value per share at full recovery to FY{y0}-{y1} normal (USD)", "value": full_value},
] + [{"item": k, "value": v} for k, v in head_summary.items()]).to_csv(OUT / "06_headline_result.csv", index=False)
print(f"\nHeadline: {s_star:.0%} of the way back -> growth {head_g:.2%} a year, margin {head_m:.2%} by FY2031, "
      f"value ${head_value:.2f}")
print(f"Full recovery ({normal_g:.2%} growth, {normal_m:.2%} margin) would be worth ${full_value:.2f}")

# ---------------------------------------------------------------------------
# STEP 4. Sensitivity table: value per share for growth (rows) x margin (columns)
# ---------------------------------------------------------------------------
g_first, g_last, g_step = A.HEATMAP_GROWTH_RANGE["value"]
m_first, m_last, m_step = A.HEATMAP_MARGIN_RANGE["value"]
growths = np.round(np.arange(g_first, g_last + g_step / 2, g_step), 4)
margins = np.round(np.arange(m_first, m_last + m_step / 2, m_step), 4)
grid = pd.DataFrame([[D.value_per_share(D.constant(g), m) for m in margins] for g in growths],
                    index=[f"{g:.0%}" for g in growths], columns=[f"{m:.0%}" for m in margins])
grid.index.name = "growth per year FY2028-31, after FY2027 at guidance (down) / operating margin by FY2031 (across)"
grid.round(2).to_csv(OUT / "06_sensitivity_value_per_share_usd.csv")

# ---------------------------------------------------------------------------
# STEP 5. Heatmap: red = worth less than today's price, blue = worth more
# ---------------------------------------------------------------------------
cmap = LinearSegmentedColormap.from_list("price_diverging", ["#b8322f", "#e98b85", "#f0efec", "#86b6ef", "#1c5cab"])
norm = TwoSlopeNorm(vcenter=PRICE, vmin=grid.values.min(), vmax=grid.values.max())
fig, ax = plt.subplots(figsize=(11, 7.5))
ax.imshow(grid.values, cmap=cmap, norm=norm, origin="lower", aspect="auto",
          extent=[m_first - m_step / 2, m_last + m_step / 2, g_first - g_step / 2, g_last + g_step / 2])
for i, g in enumerate(growths):
    for j, m in enumerate(margins):
        val = grid.values[i, j]
        dark_cell = abs(norm(val) - 0.5) > 0.38
        ax.text(m, g, f"${val:.0f}", ha="center", va="center", fontsize=8.5, color="white" if dark_cell else "#0b0b0b")
# The line where value = today's price: the Step 2 solver run on a finer list of margins
fine_m = np.arange(m_first, m_last + 1e-9, m_step / 4)
fine_g = np.array([D.implied_growth(m)[0] for m in fine_m])
ax.plot(fine_m, fine_g, color="#0b0b0b", lw=2.5)
ax.set_xlim(m_first - m_step / 2, m_last + m_step / 2)
ax.set_ylim(g_first - g_step / 2, g_last + g_step / 2)
# The three reference points are named in a legend below the chart, so no label covers a cell's value.
for (x, y, label, mk) in [(start_m, start_g, f"FY{D.BASE_FY} actual", "s"),
                          (normal_m, normal_g, f"Normal Nike, FY{y0}-{y1}", "D"),
                          (head_m, head_g, "Headline pair the price implies", "o")]:
    ax.plot(x, y, marker=mk, ms=10, mfc="white", mec="#0b0b0b", mew=2, ls="none",
            label=f"{label}: {y:.1%} growth, {x:.1%} margin")
ax.plot([], [], color="#0b0b0b", lw=2.5, label=f"Every combination worth the ${PRICE:.2f} price")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, frameon=False, fontsize=9)
ax.set_xticks(margins, [f"{m:.0%}" for m in margins])
ax.set_yticks(growths, [f"{g:.0%}" for g in growths])
ax.set_xlabel(f"Operating margin reached by FY2031 (straight line from the FY2027 guidance margin, {D.fy2027_margin():.1%})")
ax.set_ylabel("Revenue growth per year, FY2028-FY2031 (nominal; FY2027 at guidance, -8%)")
ax.set_title(f"Nike value per share (USD) by growth and margin, 5-year DCF at {D.WACC:.1%} WACC\n"
             f"Red = below the ${PRICE:.2f} price on {A.VALUATION_DATE['value']}, blue = above. "
             "Black line = combinations the price implies.", fontsize=11, loc="left")
for sp in ax.spines.values():
    sp.set_visible(False)
fig.tight_layout()
fig.savefig(CHART, dpi=150)
print(f"\nSaved {CHART.relative_to(ROOT)} and output/06_*.csv")
