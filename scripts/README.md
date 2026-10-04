# scripts

Python scripts, numbered in run order: 00 → 01 → 01b → 02 → 03 → 04 → 05 → 06a → 06 → 06b → 07 → 08 → 09 → 10. `00_get_non_sec_files.py` downloads the Damodaran, adidas and Puma files that are not stored in the repository. Scripts 01, 01b and 03 download fresh data and are only needed to update the analysis. `assumptions.py` is the single home for every modeling assumption. `dcf_model.py` is the project's one DCF; scripts 04 and 06 import it and script 05 writes the same formulas into Excel. See the top-level README for the full run instructions.
