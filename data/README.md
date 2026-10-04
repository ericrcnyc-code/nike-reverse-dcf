# data

`raw/` holds files exactly as downloaded (never edited): Nike's SEC filings and XBRL data (`10k/`, `10k_history/`, `10q/`, `8k/`, `companyfacts_*.json`), Yahoo price data, and in `competitors/` the SEC XBRL data for Lululemon, Deckers, On Holding and Under Armour. The non-SEC files (adidas and Puma annual-report pages in `competitors/`, Damodaran's equity risk premium file in `damodaran/`) are not stored in the repository; `scripts/00_get_non_sec_files.py` downloads them. `processed/` holds cleaned tables that scripts build from `raw/`.
