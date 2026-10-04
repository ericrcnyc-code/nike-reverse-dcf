# Changelog

How the model and its headline results changed while the project was built. All steps happened on 2026-10-04, with
the valuation date fixed at 2026-10-02 (share price $33.87). The current results are in
[`output/00_nike_valuation_summary.md`](output/00_nike_valuation_summary.md).

| Step | What changed | Base-case value per share |
|---|---|---|
| 1. First reverse DCF | 10-year forecast, reinvestment from a sales-to-capital ratio of 3.2, equity risk premium 4.23% (Damodaran, January 2026), WACC 9.2% | n/a (reverse DCF only) |
| 2. Excel DCF | 5-year forecast (FY2027-31) with live formulas; FY2027 growth +1% | $46.24 |
| 3. One model | The three DCF copies (script 04, Excel, script 06) replaced by `scripts/dcf_model.py`; terminal value now built from a normal 2.5%-growth FY2032 instead of repeating FY2031's working-capital build; one definition of growth (compound) and average margin (simple) everywhere | $46.84 |
| 4. Current risk premium | Equity risk premium updated to Damodaran's 1 September 2026 figure, 4.09%, verified in his data file; WACC 9.07% | $47.81 |
| 5. Q1 FY2027 results | FY2027 growth set from the first quarter (-4.3%) plus the rest of the year flat: -1.1% | $46.88 |
| 6. Nike's FY2027 guidance | FY2027 fixed at the guidance from the 1 October 2026 earnings release: revenue -8%, adjusted operating margin 5.55%; reverse DCFs now solve for FY2028-31 | **$42.17** |

Effect of step 6 on the main question: before the guidance, the price implied about 1.7% growth and a 9.3% margin by
FY2031 (26% of the way back to "normal Nike"); after it, about 2.9% growth and a 10.3% margin (48% of the way back).
The guided FY2027 starts Nike lower, so the same price needs more recovery afterwards.

Other additions along the way: segment revenue read from each 10-K (script 01b), Nike's history back to FY1993 (06a),
competitors (06b), risk checks (07), peer multiples (08, with adidas moved from calendar 2025 to the last twelve months
using its half-year reports and its minority interests added to enterprise value), the data audit (09, 256 checks, no
failures) and the guidance scenarios (10).
