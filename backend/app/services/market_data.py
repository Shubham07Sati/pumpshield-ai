import logging
import time
from dataclasses import dataclass

import yfinance as yf

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 900

# ---------------------------------------------------------------------------
# Nifty 50 — maps clean ticker (stored in DB / shown to user)
#             → Yahoo Finance ticker (used for live data)
# ---------------------------------------------------------------------------
NIFTY50_YAHOO_MAP: dict[str, str] = {
    "ADANIENT":   "ADANIENT.NS",
    "ADANIPORTS": "ADANIPORTS.NS",
    "APOLLOHOSP": "APOLLOHOSP.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "AXISBANK":   "AXISBANK.NS",
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",
    "BEL":        "BEL.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "CIPLA":      "CIPLA.NS",
    "COALINDIA":  "COALINDIA.NS",
    "DRREDDY":    "DRREDDY.NS",
    "EICHERMOT":  "EICHERMOT.NS",
    "ETERNAL":    "ETERNAL.NS",
    "GRASIM":     "GRASIM.NS",
    "HCLTECH":    "HCLTECH.NS",
    "HDFCBANK":   "HDFCBANK.NS",
    "HDFCLIFE":   "HDFCLIFE.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS",
    "HINDALCO":   "HINDALCO.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "ICICIBANK":  "ICICIBANK.NS",
    "INDUSINDBK": "INDUSINDBK.NS",
    "INFY":       "INFY.NS",
    "ITC":        "ITC.NS",
    "JIOFIN":     "JIOFIN.NS",
    "JSWSTEEL":   "JSWSTEEL.NS",
    "KOTAKBANK":  "KOTAKBANK.NS",
    "LT":         "LT.NS",
    "M&M":        "M&M.NS",
    "MARUTI":     "MARUTI.NS",
    "NTPC":       "NTPC.NS",
    "ONGC":       "ONGC.NS",
    "POWERGRID":  "POWERGRID.NS",
    "RELIANCE":   "RELIANCE.NS",
    "SBILIFE":    "SBILIFE.NS",
    "SHRIRAMFIN": "SHRIRAMFIN.NS",
    "SBIN":       "SBIN.NS",
    "SUNPHARMA":  "SUNPHARMA.NS",
    "TATACONSUM": "TATACONSUM.NS",
    "TATAMOTORS": "TMCV.NS",
    "TATASTEEL":  "TATASTEEL.NS",
    "TCS":        "TCS.NS",
    "TECHM":      "TECHM.NS",
    "TITAN":      "TITAN.NS",
    "TRENT":      "TRENT.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "WIPRO":      "WIPRO.NS",
    "NESTLEIND":  "NESTLEIND.NS",
}

# ---------------------------------------------------------------------------
# Demo / fallback snapshots — used when Yahoo Finance is unavailable
# Prices in native currency (USD for US stocks, INR for Indian stocks)
# Risk indicators reflect blue-chip stability for Nifty 50 stocks
# ---------------------------------------------------------------------------
_DEMO_SNAPSHOTS: dict[str, dict] = {
    # ── US stocks (kept for backward compatibility) ──────────────────────────
    "AAPL": {
        "company_name": "Apple Inc.",
        "current_price": 190.0,
        "avg_volume_3d": 55_000_000,
        "avg_volume_30d": 52_000_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.015,
        "institutional_ownership_pct": 62.0,
        "recent_price_change_pct": 1.2,
        "market_cap": 2_900_000_000_000,
    },
    "MSFT": {
        "company_name": "Microsoft Corporation",
        "current_price": 420.0,
        "avg_volume_3d": 22_000_000,
        "avg_volume_30d": 21_000_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.014,
        "institutional_ownership_pct": 72.0,
        "recent_price_change_pct": 0.8,
        "market_cap": 3_100_000_000_000,
    },
    "TSLA": {
        "company_name": "Tesla, Inc.",
        "current_price": 250.0,
        "avg_volume_3d": 120_000_000,
        "avg_volume_30d": 80_000_000,
        "volume_spike_ratio": 1.5,
        "daily_return_std": 0.045,
        "institutional_ownership_pct": 44.0,
        "recent_price_change_pct": 8.5,
        "market_cap": 800_000_000_000,
    },
    "GME": {
        "company_name": "GameStop Corp.",
        "current_price": 25.0,
        "avg_volume_3d": 15_000_000,
        "avg_volume_30d": 4_000_000,
        "volume_spike_ratio": 3.75,
        "daily_return_std": 0.09,
        "institutional_ownership_pct": 28.0,
        "recent_price_change_pct": 35.0,
        "market_cap": 7_500_000_000,
    },
    # ── Nifty 50 — Indian stocks (prices in INR) ──────────────────────────────
    "ADANIENT": {
        "company_name": "Adani Enterprises Ltd.",
        "current_price": 2_380.0,
        "avg_volume_3d": 2_200_000,
        "avg_volume_30d": 2_000_000,
        "volume_spike_ratio": 1.10,
        "daily_return_std": 0.028,
        "institutional_ownership_pct": 38.0,
        "recent_price_change_pct": 1.5,
        "market_cap": 2_710_000_000_000,
    },
    "ADANIPORTS": {
        "company_name": "Adani Ports and SEZ Ltd.",
        "current_price": 1_185.0,
        "avg_volume_3d": 3_500_000,
        "avg_volume_30d": 3_200_000,
        "volume_spike_ratio": 1.09,
        "daily_return_std": 0.022,
        "institutional_ownership_pct": 42.0,
        "recent_price_change_pct": 0.9,
        "market_cap": 2_560_000_000_000,
    },
    "APOLLOHOSP": {
        "company_name": "Apollo Hospitals Enterprise Ltd.",
        "current_price": 6_450.0,
        "avg_volume_3d": 450_000,
        "avg_volume_30d": 420_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.019,
        "institutional_ownership_pct": 52.0,
        "recent_price_change_pct": 1.1,
        "market_cap": 929_000_000_000,
    },
    "ASIANPAINT": {
        "company_name": "Asian Paints Ltd.",
        "current_price": 2_280.0,
        "avg_volume_3d": 1_100_000,
        "avg_volume_30d": 1_050_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 58.0,
        "recent_price_change_pct": -0.7,
        "market_cap": 2_181_000_000_000,
    },
    "AXISBANK": {
        "company_name": "Axis Bank Ltd.",
        "current_price": 1_095.0,
        "avg_volume_3d": 9_000_000,
        "avg_volume_30d": 8_500_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.018,
        "institutional_ownership_pct": 63.0,
        "recent_price_change_pct": 0.5,
        "market_cap": 3_382_000_000_000,
    },
    "BAJAJ-AUTO": {
        "company_name": "Bajaj Auto Ltd.",
        "current_price": 8_450.0,
        "avg_volume_3d": 550_000,
        "avg_volume_30d": 520_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.017,
        "institutional_ownership_pct": 55.0,
        "recent_price_change_pct": 1.3,
        "market_cap": 2_370_000_000_000,
    },
    "BAJFINANCE": {
        "company_name": "Bajaj Finance Ltd.",
        "current_price": 6_980.0,
        "avg_volume_3d": 1_800_000,
        "avg_volume_30d": 1_700_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.021,
        "institutional_ownership_pct": 61.0,
        "recent_price_change_pct": 0.8,
        "market_cap": 4_216_000_000_000,
    },
    "BAJAJFINSV": {
        "company_name": "Bajaj Finserv Ltd.",
        "current_price": 1_720.0,
        "avg_volume_3d": 2_800_000,
        "avg_volume_30d": 2_600_000,
        "volume_spike_ratio": 1.08,
        "daily_return_std": 0.019,
        "institutional_ownership_pct": 57.0,
        "recent_price_change_pct": 0.6,
        "market_cap": 2_742_000_000_000,
    },
    "BEL": {
        "company_name": "Bharat Electronics Ltd.",
        "current_price": 278.0,
        "avg_volume_3d": 18_000_000,
        "avg_volume_30d": 17_000_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.020,
        "institutional_ownership_pct": 48.0,
        "recent_price_change_pct": 1.0,
        "market_cap": 2_030_000_000_000,
    },
    "BHARTIARTL": {
        "company_name": "Bharti Airtel Ltd.",
        "current_price": 1_695.0,
        "avg_volume_3d": 6_500_000,
        "avg_volume_30d": 6_200_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.017,
        "institutional_ownership_pct": 65.0,
        "recent_price_change_pct": 0.9,
        "market_cap": 9_582_000_000_000,
    },
    "CIPLA": {
        "company_name": "Cipla Ltd.",
        "current_price": 1_490.0,
        "avg_volume_3d": 2_200_000,
        "avg_volume_30d": 2_000_000,
        "volume_spike_ratio": 1.10,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 53.0,
        "recent_price_change_pct": 0.7,
        "market_cap": 1_201_000_000_000,
    },
    "COALINDIA": {
        "company_name": "Coal India Ltd.",
        "current_price": 398.0,
        "avg_volume_3d": 9_000_000,
        "avg_volume_30d": 8_500_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 50.0,
        "recent_price_change_pct": -0.4,
        "market_cap": 2_453_000_000_000,
    },
    "DRREDDY": {
        "company_name": "Dr. Reddy's Laboratories Ltd.",
        "current_price": 1_180.0,
        "avg_volume_3d": 1_600_000,
        "avg_volume_30d": 1_500_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.018,
        "institutional_ownership_pct": 56.0,
        "recent_price_change_pct": 0.5,
        "market_cap": 986_000_000_000,
    },
    "EICHERMOT": {
        "company_name": "Eicher Motors Ltd.",
        "current_price": 4_780.0,
        "avg_volume_3d": 450_000,
        "avg_volume_30d": 420_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.018,
        "institutional_ownership_pct": 54.0,
        "recent_price_change_pct": 0.8,
        "market_cap": 1_309_000_000_000,
    },
    "ETERNAL": {
        "company_name": "Eternal Ltd.",
        "current_price": 222.0,
        "avg_volume_3d": 30_000_000,
        "avg_volume_30d": 28_000_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.025,
        "institutional_ownership_pct": 48.0,
        "recent_price_change_pct": 1.2,
        "market_cap": 1_966_000_000_000,
    },
    "GRASIM": {
        "company_name": "Grasim Industries Ltd.",
        "current_price": 2_580.0,
        "avg_volume_3d": 1_200_000,
        "avg_volume_30d": 1_100_000,
        "volume_spike_ratio": 1.09,
        "daily_return_std": 0.018,
        "institutional_ownership_pct": 52.0,
        "recent_price_change_pct": 0.6,
        "market_cap": 1_693_000_000_000,
    },
    "HCLTECH": {
        "company_name": "HCL Technologies Ltd.",
        "current_price": 1_680.0,
        "avg_volume_3d": 4_800_000,
        "avg_volume_30d": 4_500_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 60.0,
        "recent_price_change_pct": 0.9,
        "market_cap": 4_561_000_000_000,
    },
    "HDFCBANK": {
        "company_name": "HDFC Bank Ltd.",
        "current_price": 1_920.0,
        "avg_volume_3d": 13_000_000,
        "avg_volume_30d": 12_500_000,
        "volume_spike_ratio": 1.04,
        "daily_return_std": 0.014,
        "institutional_ownership_pct": 72.0,
        "recent_price_change_pct": 0.5,
        "market_cap": 14_620_000_000_000,
    },
    "HDFCLIFE": {
        "company_name": "HDFC Life Insurance Company Ltd.",
        "current_price": 695.0,
        "avg_volume_3d": 4_500_000,
        "avg_volume_30d": 4_200_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.017,
        "institutional_ownership_pct": 63.0,
        "recent_price_change_pct": 0.4,
        "market_cap": 1_491_000_000_000,
    },
    "HEROMOTOCO": {
        "company_name": "Hero MotoCorp Ltd.",
        "current_price": 4_180.0,
        "avg_volume_3d": 800_000,
        "avg_volume_30d": 760_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 51.0,
        "recent_price_change_pct": 0.6,
        "market_cap": 835_000_000_000,
    },
    "HINDALCO": {
        "company_name": "Hindalco Industries Ltd.",
        "current_price": 648.0,
        "avg_volume_3d": 11_000_000,
        "avg_volume_30d": 10_500_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.021,
        "institutional_ownership_pct": 55.0,
        "recent_price_change_pct": 0.8,
        "market_cap": 1_459_000_000_000,
    },
    "HINDUNILVR": {
        "company_name": "Hindustan Unilever Ltd.",
        "current_price": 2_290.0,
        "avg_volume_3d": 2_200_000,
        "avg_volume_30d": 2_100_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.013,
        "institutional_ownership_pct": 66.0,
        "recent_price_change_pct": -0.3,
        "market_cap": 5_376_000_000_000,
    },
    "ICICIBANK": {
        "company_name": "ICICI Bank Ltd.",
        "current_price": 1_345.0,
        "avg_volume_3d": 16_000_000,
        "avg_volume_30d": 15_500_000,
        "volume_spike_ratio": 1.03,
        "daily_return_std": 0.015,
        "institutional_ownership_pct": 68.0,
        "recent_price_change_pct": 0.7,
        "market_cap": 9_488_000_000_000,
    },
    "INDUSINDBK": {
        "company_name": "IndusInd Bank Ltd.",
        "current_price": 698.0,
        "avg_volume_3d": 7_500_000,
        "avg_volume_30d": 7_000_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.027,
        "institutional_ownership_pct": 58.0,
        "recent_price_change_pct": -1.2,
        "market_cap": 1_084_000_000_000,
    },
    "INFY": {
        "company_name": "Infosys Ltd.",
        "current_price": 1_590.0,
        "avg_volume_3d": 8_000_000,
        "avg_volume_30d": 7_500_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 62.0,
        "recent_price_change_pct": 0.9,
        "market_cap": 6_608_000_000_000,
    },
    "ITC": {
        "company_name": "ITC Ltd.",
        "current_price": 428.0,
        "avg_volume_3d": 20_000_000,
        "avg_volume_30d": 19_000_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.013,
        "institutional_ownership_pct": 59.0,
        "recent_price_change_pct": 0.4,
        "market_cap": 5_344_000_000_000,
    },
    "JIOFIN": {
        "company_name": "Jio Financial Services Ltd.",
        "current_price": 328.0,
        "avg_volume_3d": 15_000_000,
        "avg_volume_30d": 14_000_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.023,
        "institutional_ownership_pct": 44.0,
        "recent_price_change_pct": 1.3,
        "market_cap": 2_083_000_000_000,
    },
    "JSWSTEEL": {
        "company_name": "JSW Steel Ltd.",
        "current_price": 985.0,
        "avg_volume_3d": 5_500_000,
        "avg_volume_30d": 5_200_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.022,
        "institutional_ownership_pct": 50.0,
        "recent_price_change_pct": 0.6,
        "market_cap": 2_381_000_000_000,
    },
    "KOTAKBANK": {
        "company_name": "Kotak Mahindra Bank Ltd.",
        "current_price": 2_095.0,
        "avg_volume_3d": 5_000_000,
        "avg_volume_30d": 4_800_000,
        "volume_spike_ratio": 1.04,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 64.0,
        "recent_price_change_pct": 0.5,
        "market_cap": 4_165_000_000_000,
    },
    "LT": {
        "company_name": "Larsen & Toubro Ltd.",
        "current_price": 3_490.0,
        "avg_volume_3d": 2_800_000,
        "avg_volume_30d": 2_600_000,
        "volume_spike_ratio": 1.08,
        "daily_return_std": 0.017,
        "institutional_ownership_pct": 57.0,
        "recent_price_change_pct": 0.7,
        "market_cap": 4_800_000_000_000,
    },
    "M&M": {
        "company_name": "Mahindra & Mahindra Ltd.",
        "current_price": 2_980.0,
        "avg_volume_3d": 4_000_000,
        "avg_volume_30d": 3_800_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.020,
        "institutional_ownership_pct": 56.0,
        "recent_price_change_pct": 1.1,
        "market_cap": 3_702_000_000_000,
    },
    "MARUTI": {
        "company_name": "Maruti Suzuki India Ltd.",
        "current_price": 11_950.0,
        "avg_volume_3d": 750_000,
        "avg_volume_30d": 700_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 60.0,
        "recent_price_change_pct": 0.8,
        "market_cap": 3_617_000_000_000,
    },
    "NTPC": {
        "company_name": "NTPC Ltd.",
        "current_price": 328.0,
        "avg_volume_3d": 18_000_000,
        "avg_volume_30d": 17_000_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 53.0,
        "recent_price_change_pct": 0.4,
        "market_cap": 3_180_000_000_000,
    },
    "ONGC": {
        "company_name": "Oil and Natural Gas Corporation Ltd.",
        "current_price": 238.0,
        "avg_volume_3d": 22_000_000,
        "avg_volume_30d": 21_000_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.018,
        "institutional_ownership_pct": 55.0,
        "recent_price_change_pct": -0.5,
        "market_cap": 2_993_000_000_000,
    },
    "POWERGRID": {
        "company_name": "Power Grid Corporation of India Ltd.",
        "current_price": 318.0,
        "avg_volume_3d": 16_000_000,
        "avg_volume_30d": 15_500_000,
        "volume_spike_ratio": 1.03,
        "daily_return_std": 0.015,
        "institutional_ownership_pct": 54.0,
        "recent_price_change_pct": 0.3,
        "market_cap": 2_964_000_000_000,
    },
    "RELIANCE": {
        "company_name": "Reliance Industries Ltd.",
        "current_price": 1_445.0,
        "avg_volume_3d": 22_000_000,
        "avg_volume_30d": 21_000_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.015,
        "institutional_ownership_pct": 58.0,
        "recent_price_change_pct": 0.6,
        "market_cap": 19_520_000_000_000,
    },
    "SBILIFE": {
        "company_name": "SBI Life Insurance Company Ltd.",
        "current_price": 1_580.0,
        "avg_volume_3d": 2_200_000,
        "avg_volume_30d": 2_100_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.017,
        "institutional_ownership_pct": 60.0,
        "recent_price_change_pct": 0.5,
        "market_cap": 1_582_000_000_000,
    },
    "SHRIRAMFIN": {
        "company_name": "Shriram Finance Ltd.",
        "current_price": 692.0,
        "avg_volume_3d": 3_500_000,
        "avg_volume_30d": 3_300_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.021,
        "institutional_ownership_pct": 48.0,
        "recent_price_change_pct": 0.7,
        "market_cap": 1_302_000_000_000,
    },
    "SBIN": {
        "company_name": "State Bank of India",
        "current_price": 775.0,
        "avg_volume_3d": 28_000_000,
        "avg_volume_30d": 27_000_000,
        "volume_spike_ratio": 1.04,
        "daily_return_std": 0.017,
        "institutional_ownership_pct": 56.0,
        "recent_price_change_pct": 0.6,
        "market_cap": 6_919_000_000_000,
    },
    "SUNPHARMA": {
        "company_name": "Sun Pharmaceutical Industries Ltd.",
        "current_price": 1_690.0,
        "avg_volume_3d": 3_800_000,
        "avg_volume_30d": 3_600_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.017,
        "institutional_ownership_pct": 55.0,
        "recent_price_change_pct": 0.8,
        "market_cap": 4_059_000_000_000,
    },
    "TATACONSUM": {
        "company_name": "Tata Consumer Products Ltd.",
        "current_price": 1_045.0,
        "avg_volume_3d": 3_500_000,
        "avg_volume_30d": 3_300_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.018,
        "institutional_ownership_pct": 52.0,
        "recent_price_change_pct": 0.5,
        "market_cap": 1_041_000_000_000,
    },
    "TATAMOTORS": {
        "company_name": "Tata Motors Ltd.",
        "current_price": 695.0,
        "avg_volume_3d": 18_000_000,
        "avg_volume_30d": 17_000_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.024,
        "institutional_ownership_pct": 50.0,
        "recent_price_change_pct": 1.0,
        "market_cap": 2_292_000_000_000,
    },
    "TATASTEEL": {
        "company_name": "Tata Steel Ltd.",
        "current_price": 152.0,
        "avg_volume_3d": 55_000_000,
        "avg_volume_30d": 52_000_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.022,
        "institutional_ownership_pct": 48.0,
        "recent_price_change_pct": 0.7,
        "market_cap": 1_904_000_000_000,
    },
    "TCS": {
        "company_name": "Tata Consultancy Services Ltd.",
        "current_price": 3_590.0,
        "avg_volume_3d": 4_200_000,
        "avg_volume_30d": 4_000_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.014,
        "institutional_ownership_pct": 64.0,
        "recent_price_change_pct": 0.6,
        "market_cap": 12_990_000_000_000,
    },
    "TECHM": {
        "company_name": "Tech Mahindra Ltd.",
        "current_price": 1_590.0,
        "avg_volume_3d": 4_500_000,
        "avg_volume_30d": 4_300_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.019,
        "institutional_ownership_pct": 55.0,
        "recent_price_change_pct": 0.7,
        "market_cap": 1_549_000_000_000,
    },
    "TITAN": {
        "company_name": "Titan Company Ltd.",
        "current_price": 3_380.0,
        "avg_volume_3d": 1_500_000,
        "avg_volume_30d": 1_400_000,
        "volume_spike_ratio": 1.07,
        "daily_return_std": 0.019,
        "institutional_ownership_pct": 53.0,
        "recent_price_change_pct": 0.8,
        "market_cap": 3_002_000_000_000,
    },
    "TRENT": {
        "company_name": "Trent Ltd.",
        "current_price": 5_450.0,
        "avg_volume_3d": 900_000,
        "avg_volume_30d": 850_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.024,
        "institutional_ownership_pct": 48.0,
        "recent_price_change_pct": 1.4,
        "market_cap": 1_947_000_000_000,
    },
    "ULTRACEMCO": {
        "company_name": "UltraTech Cement Ltd.",
        "current_price": 9_980.0,
        "avg_volume_3d": 650_000,
        "avg_volume_30d": 620_000,
        "volume_spike_ratio": 1.05,
        "daily_return_std": 0.016,
        "institutional_ownership_pct": 57.0,
        "recent_price_change_pct": 0.5,
        "market_cap": 2_877_000_000_000,
    },
    "WIPRO": {
        "company_name": "Wipro Ltd.",
        "current_price": 276.0,
        "avg_volume_3d": 14_000_000,
        "avg_volume_30d": 13_500_000,
        "volume_spike_ratio": 1.04,
        "daily_return_std": 0.015,
        "institutional_ownership_pct": 58.0,
        "recent_price_change_pct": 0.4,
        "market_cap": 2_891_000_000_000,
    },
    "NESTLEIND": {
        "company_name": "Nestlé India Ltd.",
        "current_price": 2_195.0,
        "avg_volume_3d": 550_000,
        "avg_volume_30d": 520_000,
        "volume_spike_ratio": 1.06,
        "daily_return_std": 0.014,
        "institutional_ownership_pct": 62.0,
        "recent_price_change_pct": 0.3,
        "market_cap": 2_116_000_000_000,
    },
}


@dataclass
class MarketSnapshot:
    symbol: str
    company_name: str
    current_price: float | None
    avg_volume_3d: float | None
    avg_volume_30d: float | None
    volume_spike_ratio: float | None
    daily_return_std: float | None
    institutional_ownership_pct: float | None
    recent_price_change_pct: float | None
    market_cap: float | None


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _yf_ticker(symbol: str) -> str:
    """Return the Yahoo Finance ticker for a given clean symbol.
    Nifty 50 stocks are on NSE and need the .NS suffix."""
    return NIFTY50_YAHOO_MAP.get(symbol, symbol)


def _get_cached(symbol: str) -> MarketSnapshot | None:
    entry = _cache.get(symbol)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        del _cache[symbol]
        return None
    return MarketSnapshot(**data)


def _set_cache(symbol: str, snapshot: MarketSnapshot) -> None:
    _cache[symbol] = (time.time(), snapshot.__dict__)


def _demo_snapshot(symbol: str) -> MarketSnapshot | None:
    demo = _DEMO_SNAPSHOTS.get(symbol)
    if not demo:
        return None
    logger.info("Using demo market data for %s (live data unavailable)", symbol)
    return MarketSnapshot(symbol=symbol, **demo)


def _fetch_history(yf_symbol: str):
    try:
        data = yf.download(yf_symbol, period="3mo", progress=False, auto_adjust=True)
        if data is not None and not data.empty:
            return data
    except Exception as exc:
        logger.warning("yf.download failed for %s: %s", yf_symbol, exc)

    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="3mo")
        if hist is not None and not hist.empty:
            return hist
    except Exception as exc:
        logger.warning("Ticker.history failed for %s: %s", yf_symbol, exc)

    return None


def _fetch_info(yf_symbol: str) -> dict:
    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        return info if isinstance(info, dict) else {}
    except Exception as exc:
        logger.warning("ticker.info failed for %s: %s", yf_symbol, exc)
        return {}


def fetch_price_series(symbol: str, days: int = 30) -> list[dict]:
    """Return recent daily close/volume points for charting."""
    symbol = normalize_symbol(symbol)
    yf_sym = _yf_ticker(symbol)
    hist = _fetch_history(yf_sym)
    if hist is None or hist.empty:
        demo = _DEMO_SNAPSHOTS.get(symbol)
        if not demo:
            return []
        base = demo.get("current_price") or 100.0
        return [
            {"date": f"D-{days - i}", "close": round(base * (1 + (i - days / 2) * 0.002), 2), "volume": demo.get("avg_volume_30d", 1_000_000)}
            for i in range(days)
        ]

    if hasattr(hist.columns, "levels") and hist.columns.nlevels > 1:
        try:
            hist = hist.xs(yf_sym, axis=1, level=1)
        except (KeyError, ValueError):
            pass

    close_col = "Close" if "Close" in hist.columns else None
    vol_col = "Volume" if "Volume" in hist.columns else None
    if not close_col:
        return []

    tail = hist.tail(days)
    series = []
    for idx, row in tail.iterrows():
        date_label = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        point = {"date": date_label, "close": round(float(row[close_col]), 2)}
        if vol_col and row.get(vol_col) is not None:
            point["volume"] = int(float(row[vol_col]))
        series.append(point)
    return series


def snapshot_to_context(snapshot: MarketSnapshot) -> dict:
    return {
        "company_name": snapshot.company_name,
        "current_price": snapshot.current_price,
        "volume_spike_ratio": snapshot.volume_spike_ratio,
        "daily_return_std": snapshot.daily_return_std,
        "institutional_ownership_pct": snapshot.institutional_ownership_pct,
        "recent_price_change_pct": snapshot.recent_price_change_pct,
        "market_cap": snapshot.market_cap,
        "avg_volume_3d": snapshot.avg_volume_3d,
        "avg_volume_30d": snapshot.avg_volume_30d,
    }


def fetch_market_snapshot(symbol: str) -> MarketSnapshot:
    symbol = normalize_symbol(symbol)
    cached = _get_cached(symbol)
    if cached:
        return cached

    # Use .NS suffix for Nifty 50 stocks when querying Yahoo Finance
    yf_sym = _yf_ticker(symbol)

    hist = _fetch_history(yf_sym)
    info = _fetch_info(yf_sym)

    if hist is None or hist.empty:
        demo = _demo_snapshot(symbol)
        if demo:
            _set_cache(symbol, demo)
            return demo
        if not info.get("shortName") and not info.get("longName"):
            raise ValueError(f"Could not find market data for symbol '{symbol}'")

    avg_volume_3d = None
    avg_volume_30d = None
    volume_spike_ratio = None
    daily_return_std = None
    recent_price_change_pct = None
    current_price = None

    if hist is not None and not hist.empty:
        if hasattr(hist.columns, "levels") and hist.columns.nlevels > 1:
            try:
                hist = hist.xs(yf_sym, axis=1, level=1)
            except (KeyError, ValueError):
                pass

        vol_col = "Volume" if "Volume" in hist.columns else None
        close_col = "Close" if "Close" in hist.columns else None

        if vol_col:
            volumes = hist[vol_col].dropna()
            if len(volumes) >= 3:
                avg_volume_3d = float(volumes.tail(3).mean())
            if len(volumes) >= 30:
                avg_volume_30d = float(volumes.tail(30).mean())
            elif len(volumes) > 0:
                avg_volume_30d = float(volumes.mean())
            if avg_volume_3d and avg_volume_30d and avg_volume_30d > 0:
                volume_spike_ratio = avg_volume_3d / avg_volume_30d

        if close_col:
            closes = hist[close_col].dropna()
            if len(closes) >= 1:
                current_price = float(closes.iloc[-1])
            if len(closes) >= 2:
                returns = closes.pct_change().dropna()
                daily_return_std = float(returns.std()) if len(returns) > 0 else None
                if len(closes) >= 4:
                    recent_price_change_pct = float(
                        (closes.iloc[-1] - closes.iloc[-4]) / closes.iloc[-4] * 100
                    )

    institutional = info.get("heldPercentInstitutions")
    institutional_pct = float(institutional * 100) if institutional is not None else None

    snapshot = MarketSnapshot(
        symbol=symbol,
        company_name=info.get("longName") or info.get("shortName") or symbol,
        current_price=info.get("currentPrice") or info.get("regularMarketPrice") or current_price,
        avg_volume_3d=avg_volume_3d,
        avg_volume_30d=avg_volume_30d,
        volume_spike_ratio=volume_spike_ratio,
        daily_return_std=daily_return_std,
        institutional_ownership_pct=institutional_pct,
        recent_price_change_pct=recent_price_change_pct,
        market_cap=info.get("marketCap"),
    )

    _set_cache(symbol, snapshot)
    return snapshot
