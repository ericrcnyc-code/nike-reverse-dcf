"""
03_market_inputs.py  -  Download the market data the DCF needs and estimate Nike's beta

WHAT THIS DOES, IN PLAIN LANGUAGE
---------------------------------
The SEC does not publish market prices or interest rates, so these come from
Yahoo Finance (non-SEC, clearly labelled). This script:
1. Downloads, for the same dates, daily data for:
     NKE    Nike's share price
     ^GSPC  the S&P 500 index (stands in for "the whole stock market")
     ^TNX   the 10-year US Treasury yield (Yahoo quotes it in percent, so 5.28 = 5.28%)
   and saves the raw table to data/raw/ untouched.
2. Estimates Nike's BETA: how much Nike's stock tends to move when the market
   moves 1%. Beta 1.2 means Nike typically moves about 1.2% for each 1% market move.
   Method: take month-end prices for the last 60 months, turn them into monthly
   % returns, and fit a straight line  Nike return = a + beta x market return.
   The slope of that line is beta. Every month's returns are saved so you can
   redo it in Excel with =SLOPE(nike_returns, market_returns).
3. Prints the latest Nike price and 10-year yield.

The numbers this prints get copied BY HAND into scripts/assumptions.py (with the
date), so the model only ever reads assumptions from that one file. Re-run this
script and update assumptions.py when you want fresher market data.

HOW TO RUN
----------
    python3 scripts/03_market_inputs.py
Needs: pandas, yfinance.
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

import assumptions as A

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"
OUTPUT = PROJECT / "output"

# Download window: enough history for 60 monthly returns before the valuation date.
END = pd.Timestamp(A.VALUATION_DATE["value"])
START = END - pd.DateOffset(months=A.BETA_LOOKBACK_MONTHS["value"] + 2)

# ---------------------------------------------------------------------------
# STEP 1: DOWNLOAD AND SAVE RAW DATA
# ---------------------------------------------------------------------------
tickers = ["NKE", "^GSPC", "^TNX"]
raw = yf.download(tickers, start=START.strftime("%Y-%m-%d"),
                  end=(END + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                  auto_adjust=False, progress=False)
raw_path = RAW / f"market_data_NKE_GSPC_TNX_yfinance_{END.date()}.csv"
raw.to_csv(raw_path)

close = raw["Close"]          # actual traded price / yield
adj = raw["Adj Close"]        # price adjusted for dividends (for returns)

# ---------------------------------------------------------------------------
# STEP 2: MONTHLY RETURNS AND BETA
# ---------------------------------------------------------------------------
# Adjusted close includes dividends, so a % change in it is the total return.
monthly = adj[["NKE", "^GSPC"]].resample("ME").last()
# Drop the current, unfinished month so every return covers a full month.
monthly = monthly[monthly.index < END.replace(day=1)]
returns = monthly.pct_change().dropna().tail(A.BETA_LOOKBACK_MONTHS["value"])
returns.columns = ["Nike monthly return", "S&P 500 monthly return"]

# Slope of a straight-line fit = covariance(Nike, market) / variance(market)
cov = returns["Nike monthly return"].cov(returns["S&P 500 monthly return"])
var = returns["S&P 500 monthly return"].var()
beta = cov / var

OUTPUT.mkdir(exist_ok=True)
returns.round(6).to_csv(OUTPUT / "03_beta_monthly_returns.csv", index_label="Month end")
pd.DataFrame([
    {"item": "Months used", "value": len(returns)},
    {"item": "First month", "value": returns.index[0].date()},
    {"item": "Last month", "value": returns.index[-1].date()},
    {"item": "Covariance(Nike, S&P 500)", "value": round(cov, 6)},
    {"item": "Variance(S&P 500)", "value": round(var, 6)},
    {"item": "Beta = covariance / variance", "value": round(beta, 3)},
]).to_csv(OUTPUT / "03_beta_summary.csv", index=False)

# ---------------------------------------------------------------------------
# STEP 3: LATEST PRICE AND 10-YEAR YIELD
# ---------------------------------------------------------------------------
last_day = close["NKE"].dropna().index[-1]
print(f"Raw data saved: {raw_path.name}")
print(f"Last trading day: {last_day.date()}")
print(f"NKE close:        {close['NKE'].dropna().iloc[-1]:.2f} USD")
print(f"10-year yield:    {close['^TNX'].dropna().iloc[-1]:.3f} %")
print(f"Beta ({len(returns)} monthly returns, {returns.index[0].date()} to {returns.index[-1].date()}): {beta:.3f}")
