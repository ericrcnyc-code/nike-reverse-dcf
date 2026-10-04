"""
10_memo_scenarios.py  -  Bull, base and bear values for the investment memo, starting from Nike's FY2027 guidance

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
On 2026-10-01 Nike guided FY2027 revenue down "high-single digits" and adjusted
EPS of USD 1.15-1.35. Since 2026-10-04 the project's one DCF (dcf_model.py) fixes
FY2027 at that guidance in every run. This script:

  1. Turns the guidance into an FY2027 operating margin (step by step, saved to CSV):
       net income      = adjusted EPS x diluted shares
       pre-tax income  = net income / (1 - 25% tax)
       operating income = pre-tax income - non-operating income (about USD 103m, as in FY2026)
       revenue         = FY2026 revenue x (1 + guided growth)
       margin          = operating income / revenue
     This is the ADJUSTED margin: it leaves out the ~USD 0.3bn of Pace restructuring charges.
     It checks that the mid case equals FY2027_OPERATING_MARGIN in assumptions.py, the value
     the DCF uses.
  2. Values the memo's bear, base and bull paths (MEMO_SCENARIOS in assumptions.py) with
     the project's one DCF. Each path starts at the guidance margin in FY2027 and moves in a
     straight line to its FY2031 margin. The memo's base (10.5% margin) is more cautious than
     the project base case (12.5%), which is listed for comparison.
  3. Reverse DCF answers for the memo: what FY2031 margin does the USD 33.87 price need if
     growth recovers 3%/4%/4%/4%, and what FY2028-31 growth does it need at 9.3%-10.5% margins?

Outputs
  output/10_guidance_margin.csv     the guidance-to-margin steps (low, mid, high)
  output/10_memo_scenarios.csv      value per share for each scenario, plus its FY2031 revenue and margin
  output/10_memo_forecasts.csv      year-by-year forecast for each scenario
  output/10_implied_with_guidance.csv  the reverse-DCF answers with FY2027 at guidance
"""

from pathlib import Path

import pandas as pd

import assumptions as A
import dcf_model as D

OUT = Path(__file__).resolve().parent.parent / "output"
v = D.v

# --- 1. Guidance -> FY2027 operating margin ---------------------------------
guide = v("GUIDANCE_FY2027")
shares = D.balance_sheet()["shares"]
base_revenue = D.base_year()["revenue"]
rows = []
for label, eps, growth in [("Low", guide["adjusted_eps_low"], guide["revenue_growth_low"]),
                           ("Mid", (guide["adjusted_eps_low"] + guide["adjusted_eps_high"]) / 2,
                            (guide["revenue_growth_low"] + guide["revenue_growth_high"]) / 2),
                           ("High", guide["adjusted_eps_high"], guide["revenue_growth_high"])]:
    net_income = eps * shares
    pretax = net_income / (1 - guide["tax_rate"])
    op_income = pretax - v("NON_OPERATING_INCOME_FY2027")
    revenue = base_revenue * (1 + growth)
    rows.append({"Case": label, "Adjusted EPS (USD)": eps, "Diluted shares (millions)": shares,
                 "Net income = EPS x shares (USD m)": net_income,
                 "Pre-tax income = net income / (1 - tax) (USD m)": pretax,
                 "Operating income = pre-tax - non-operating (USD m)": op_income,
                 "Revenue growth": growth, "Revenue = FY2026 x (1 + growth) (USD m)": revenue,
                 "Operating margin = operating income / revenue": op_income / revenue,
                 "P/E at share price on adjusted EPS": v("SHARE_PRICE") / eps})
guidance = pd.DataFrame(rows)
guidance.to_csv(OUT / "10_guidance_margin.csv", index=False)
m27 = guidance.loc[guidance["Case"] == "Mid", "Operating margin = operating income / revenue"].item()
print(f"FY2027 adjusted operating margin implied by guidance (mid): {m27:.2%}")
assert abs(m27 - D.fy2027_margin()) < 0.00005, f"assumptions.py FY2027_OPERATING_MARGIN {D.fy2027_margin()} != {m27}"


# --- 2. Scenarios ------------------------------------------------------------
summary, forecasts = [], []
for name, s in v("MEMO_SCENARIOS").items():
    value, table, _ = D.run(s["growth"], s["margin_fy2031"])
    table.insert(0, "Scenario", name)
    forecasts.append(table)
    last = table.iloc[-1]
    summary.append({"Scenario": name, "Value per share (USD)": value,
                    "vs share price": value / v("SHARE_PRICE") - 1,
                    "FY2031 revenue (USD m)": last["Revenue (USD m)"],
                    "FY2031 operating margin": last["Operating margin"],
                    "FY2031 operating income (USD m)": last["Operating income (USD m)"]})
value, table, _ = D.run(D.base_case_growth())
last = table.iloc[-1]
summary.append({"Scenario": "Project base case (12.5% margin, for comparison)", "Value per share (USD)": value,
                "vs share price": value / v("SHARE_PRICE") - 1, "FY2031 revenue (USD m)": last["Revenue (USD m)"],
                "FY2031 operating margin": last["Operating margin"],
                "FY2031 operating income (USD m)": last["Operating income (USD m)"]})
pd.DataFrame(summary).to_csv(OUT / "10_memo_scenarios.csv", index=False)
pd.concat(forecasts).to_csv(OUT / "10_memo_forecasts.csv", index=False)
print(pd.DataFrame(summary)[["Scenario", "Value per share (USD)"]].round(2).to_string(index=False))

# --- 3. Reverse DCF with FY2027 at guidance ----------------------------------
price = v("SHARE_PRICE")
base_growth = v("MEMO_SCENARIOS")["Base"]["growth"]
implied_margin, _ = D.bisect(lambda m: D.value_per_share(base_growth, m) - price, 0.0, 0.30)
implied = [{"Question": "FY2031 margin the price needs, growth -8%/3%/4%/4%/4%", "Answer": implied_margin}]
for m in [0.093, 0.10, 0.105]:
    g, _ = D.implied_growth(m)
    implied.append({"Question": f"FY2028-31 growth per year the price needs at a {m:.1%} FY2031 margin", "Answer": g})
pd.DataFrame(implied).to_csv(OUT / "10_implied_with_guidance.csv", index=False)
print(pd.DataFrame(implied).to_string(index=False))
