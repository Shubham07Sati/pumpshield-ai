#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Risk Score Evaluator for Nifty 50.

Strategy (no ticker.info calls — avoids Yahoo Finance 429 blocks entirely):
  1. Single batch yf.download() for all 50 tickers — 3 months of OHLCV
  2. Compute volume_spike_ratio, daily_return_std, recent_price_change_pct
     from actual historical data
  3. Institutional ownership from a static NSE/BSE lookup table
     (publicly available; updated periodically from stock exchange filings)
  4. Run risk engine → push/update Notion pages

Usage (from the backend directory):
    python scripts/real_risk_eval.py              # full run -> Notion
    python scripts/real_risk_eval.py --dry-run    # analyse only, no Notion
    python scripts/real_risk_eval.py --symbol TCS # single stock
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import yfinance as yf
import pandas as pd

from app.config import settings
from app.services.risk_engine import calculate_risk
from app.services.market_data import MarketSnapshot, NIFTY50_YAHOO_MAP
from app.services.notion_service import (
    NOTION_API_BASE,
    _normalize_database_id,
    _notion_headers,
    is_notion_configured,
)

# ---------------------------------------------------------------------------
# Static company metadata for Nifty 50
# Institutional ownership (%) from NSE/BSE quarterly shareholding data (Q1 2025)
# Source: NSE India shareholding pattern disclosures
# ---------------------------------------------------------------------------
NIFTY50_META: dict[str, dict] = {
    "ADANIENT":   {"name": "Adani Enterprises Ltd.",            "inst_pct": 18.2},
    "ADANIPORTS": {"name": "Adani Ports and SEZ Ltd.",          "inst_pct": 21.5},
    "APOLLOHOSP": {"name": "Apollo Hospitals Enterprise Ltd.",  "inst_pct": 48.3},
    "ASIANPAINT": {"name": "Asian Paints Ltd.",                 "inst_pct": 52.1},
    "AXISBANK":   {"name": "Axis Bank Ltd.",                    "inst_pct": 59.4},
    "BAJAJ-AUTO": {"name": "Bajaj Auto Ltd.",                   "inst_pct": 44.7},
    "BAJFINANCE": {"name": "Bajaj Finance Ltd.",                "inst_pct": 58.2},
    "BAJAJFINSV": {"name": "Bajaj Finserv Ltd.",               "inst_pct": 51.6},
    "BEL":        {"name": "Bharat Electronics Ltd.",           "inst_pct": 30.8},
    "BHARTIARTL": {"name": "Bharti Airtel Ltd.",               "inst_pct": 61.3},
    "CIPLA":      {"name": "Cipla Ltd.",                        "inst_pct": 47.9},
    "COALINDIA":  {"name": "Coal India Ltd.",                   "inst_pct": 22.4},
    "DRREDDY":    {"name": "Dr. Reddy's Laboratories Ltd.",     "inst_pct": 52.7},
    "EICHERMOT":  {"name": "Eicher Motors Ltd.",               "inst_pct": 49.1},
    "ETERNAL":    {"name": "Eternal Ltd.",                      "inst_pct": 38.5},
    "GRASIM":     {"name": "Grasim Industries Ltd.",            "inst_pct": 47.3},
    "HCLTECH":    {"name": "HCL Technologies Ltd.",             "inst_pct": 53.8},
    "HDFCBANK":   {"name": "HDFC Bank Ltd.",                   "inst_pct": 68.4},
    "HDFCLIFE":   {"name": "HDFC Life Insurance Company Ltd.", "inst_pct": 59.2},
    "HEROMOTOCO": {"name": "Hero MotoCorp Ltd.",               "inst_pct": 44.6},
    "HINDALCO":   {"name": "Hindalco Industries Ltd.",          "inst_pct": 50.3},
    "HINDUNILVR": {"name": "Hindustan Unilever Ltd.",           "inst_pct": 62.8},
    "ICICIBANK":  {"name": "ICICI Bank Ltd.",                   "inst_pct": 64.7},
    "INDUSINDBK": {"name": "IndusInd Bank Ltd.",               "inst_pct": 55.9},
    "INFY":       {"name": "Infosys Ltd.",                      "inst_pct": 58.6},
    "ITC":        {"name": "ITC Ltd.",                          "inst_pct": 55.4},
    "JIOFIN":     {"name": "Jio Financial Services Ltd.",       "inst_pct": 37.2},
    "JSWSTEEL":   {"name": "JSW Steel Ltd.",                   "inst_pct": 46.1},
    "KOTAKBANK":  {"name": "Kotak Mahindra Bank Ltd.",         "inst_pct": 61.5},
    "LT":         {"name": "Larsen & Toubro Ltd.",              "inst_pct": 53.9},
    "M&M":        {"name": "Mahindra & Mahindra Ltd.",          "inst_pct": 51.2},
    "MARUTI":     {"name": "Maruti Suzuki India Ltd.",          "inst_pct": 56.8},
    "NTPC":       {"name": "NTPC Ltd.",                         "inst_pct": 24.6},
    "ONGC":       {"name": "Oil and Natural Gas Corp. Ltd.",    "inst_pct": 21.8},
    "POWERGRID":  {"name": "Power Grid Corporation Ltd.",       "inst_pct": 23.1},
    "RELIANCE":   {"name": "Reliance Industries Ltd.",          "inst_pct": 54.3},
    "SBILIFE":    {"name": "SBI Life Insurance Co. Ltd.",      "inst_pct": 57.4},
    "SHRIRAMFIN": {"name": "Shriram Finance Ltd.",             "inst_pct": 42.8},
    "SBIN":       {"name": "State Bank of India",              "inst_pct": 25.6},
    "SUNPHARMA":  {"name": "Sun Pharmaceutical Ind. Ltd.",     "inst_pct": 52.1},
    "TATACONSUM": {"name": "Tata Consumer Products Ltd.",      "inst_pct": 47.6},
    "TATAMOTORS": {"name": "Tata Motors Ltd.",                 "inst_pct": 46.9},
    "TATASTEEL":  {"name": "Tata Steel Ltd.",                  "inst_pct": 44.2},
    "TCS":        {"name": "Tata Consultancy Services Ltd.",   "inst_pct": 60.3},
    "TECHM":      {"name": "Tech Mahindra Ltd.",               "inst_pct": 50.7},
    "TITAN":      {"name": "Titan Company Ltd.",               "inst_pct": 49.4},
    "TRENT":      {"name": "Trent Ltd.",                       "inst_pct": 43.1},
    "ULTRACEMCO": {"name": "UltraTech Cement Ltd.",            "inst_pct": 55.3},
    "WIPRO":      {"name": "Wipro Ltd.",                       "inst_pct": 53.6},
    "NESTLEIND":  {"name": "Nestle India Ltd.",                "inst_pct": 59.8},
}


def parse_chart_to_df(data: dict) -> pd.DataFrame:
    result = data.get("chart", {}).get("result", [])
    if not result:
        return pd.DataFrame()
    first = result[0]
    timestamp = first.get("timestamp", [])
    if not timestamp:
        return pd.DataFrame()
    quote = first.get("indicators", {}).get("quote", [])
    if not quote:
        return pd.DataFrame()
    q = quote[0]
    
    opens = q.get("open", [])
    highs = q.get("high", [])
    lows = q.get("low", [])
    closes = q.get("close", [])
    volumes = q.get("volume", [])
    
    n = len(timestamp)
    opens = (opens + [None]*n)[:n]
    highs = (highs + [None]*n)[:n]
    lows = (lows + [None]*n)[:n]
    closes = (closes + [None]*n)[:n]
    volumes = (volumes + [None]*n)[:n]
    
    df = pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": volumes
    }, index=pd.to_datetime(timestamp, unit="s"))
    return df


async def batch_download(symbols: list[str]) -> dict[str, pd.DataFrame]:
    print(">> Batch-downloading 3 months OHLCV for Nifty 50 stocks...")
    hist_map = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    async def fetch_one(client, symbol):
        yf_symbol = NIFTY50_YAHOO_MAP.get(symbol, f"{symbol}.NS")
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{yf_symbol}?range=3mo&interval=1d"
        try:
            resp = await client.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                df = parse_chart_to_df(resp.json())
                if not df.empty:
                    hist_map[symbol] = df
                    return True
            return False
        except Exception as e:
            return False

    async with httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=15, max_connections=30)) as client:
        tasks = [fetch_one(client, sym) for sym in symbols]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r)
        print(f"   Downloaded {success_count} / {len(symbols)} tickers successfully.")
        
    return hist_map

# ---------------------------------------------------------------------------
# Step 2: Build MarketSnapshot purely from per-ticker history + static metadata
# ---------------------------------------------------------------------------
def build_snapshot(symbol: str, hist_map: dict) -> MarketSnapshot:
    meta = NIFTY50_META.get(symbol, {})
    company_name = meta.get("name", symbol)
    institutional_pct = meta.get("inst_pct", None)

    hist = hist_map.get(symbol)  # pre-downloaded DataFrame or None

    avg_volume_3d = None
    avg_volume_30d = None
    volume_spike_ratio = None
    daily_return_std = None
    recent_price_change_pct = None
    current_price = None

    if hist is not None and not hist.empty:
        vol_col   = "Volume" if "Volume" in hist.columns else None
        close_col = "Close"  if "Close"  in hist.columns else None

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

    return MarketSnapshot(
        symbol=symbol,
        company_name=company_name,
        current_price=current_price,
        avg_volume_3d=avg_volume_3d,
        avg_volume_30d=avg_volume_30d,
        volume_spike_ratio=volume_spike_ratio,
        daily_return_std=daily_return_std,
        institutional_ownership_pct=institutional_pct,
        recent_price_change_pct=recent_price_change_pct,
        market_cap=None,
    )


# ---------------------------------------------------------------------------
# Notion helpers
# ---------------------------------------------------------------------------
async def find_existing_page(
    client: httpx.AsyncClient, database_id: str, symbol: str
) -> str | None:
    payload = {
        "filter": {
            "property": "Analysis ID",
            "rich_text": {"equals": f"bulk-{symbol}"},
        }
    }
    try:
        resp = await client.post(
            f"{NOTION_API_BASE}/databases/{database_id}/query",
            json=payload,
            headers=_notion_headers(),
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0]["id"] if results else None
    except Exception:
        return None


def _risk_label(level: str) -> str:
    return "Red" if level == "red" else "Green"


def _build_explanation(symbol: str, snap: MarketSnapshot, assessment) -> str:
    level = "HIGH" if assessment.risk_level == "red" else "LOW"
    reasons = [f"* {i.detail}" for i in assessment.indicators if i.score > 0]
    if not reasons:
        reasons = ["* No significant manipulation indicators detected."]
    data_line = (
        f"vol_spike={snap.volume_spike_ratio:.2f}x | "
        f"std={snap.daily_return_std:.3f} | "
        f"3d_chg={snap.recent_price_change_pct:+.2f}% | "
        f"inst={snap.institutional_ownership_pct:.1f}%"
        if all(x is not None for x in [
            snap.volume_spike_ratio, snap.daily_return_std,
            snap.recent_price_change_pct, snap.institutional_ownership_pct,
        ])
        else "(partial data)"
    )
    return (
        f"Risk Score: {assessment.risk_score}/100 ({level} risk) [REAL DATA]\n\n"
        f"{snap.company_name} ({symbol}) - Nifty 50\n"
        f"{data_line}\n\n"
        + "\n".join(reasons)
    )


async def upsert_notion_page(
    client: httpx.AsyncClient,
    database_id: str,
    symbol: str,
    snap: MarketSnapshot,
    assessment,
    explanation: str,
) -> tuple[bool, str]:
    props = {
        "Stock":       {"title": [{"text": {"content": symbol}}]},
        "User":        {"rich_text": [{"text": {"content": "real-risk-eval / nifty50"}}]},
        "Risk Score":  {"number": assessment.risk_score},
        "Risk Level":  {"select": {"name": _risk_label(assessment.risk_level)}},
        "Explanation": {"rich_text": [{"text": {"content": explanation[:2000]}}]},
        "Timestamp": {
            "date": {
                "start": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat()
            }
        },
        "Analysis ID": {"rich_text": [{"text": {"content": f"bulk-{symbol}"}}]},
    }
    page_id = await find_existing_page(client, database_id, symbol)
    try:
        if page_id:
            resp = await client.patch(
                f"{NOTION_API_BASE}/pages/{page_id}",
                json={"properties": props},
                headers=_notion_headers(),
            )
        else:
            resp = await client.post(
                f"{NOTION_API_BASE}/pages",
                json={"parent": {"database_id": database_id}, "properties": props},
                headers=_notion_headers(),
            )
        resp.raise_for_status()
        return True, "updated" if page_id else "created"
    except httpx.HTTPStatusError as exc:
        print(f"\n  [X] Notion error ({exc.response.status_code}): {exc.response.text[:200]}")
        return False, "error"
    except Exception as exc:
        print(f"\n  [X] Notion error: {exc}")
        return False, "error"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(symbols: list[str], dry_run: bool) -> None:
    if not dry_run and not is_notion_configured():
        print("[X] Notion not configured. Set NOTION_TOKEN and NOTION_DATABASE_ID in .env")
        sys.exit(1)

    database_id = _normalize_database_id(settings.notion_database_id) if not dry_run else ""

    print("\n" + "=" * 66)
    print(f"  PumpShield AI - Real Risk Evaluator  {'[DRY RUN]' if dry_run else '[LIVE]'}")
    print("=" * 66)
    print(f"  Stocks : {len(symbols)}")
    print(f"  Mode   : {'dry-run (no Notion writes)' if dry_run else 'live (update/create Notion pages)'}")
    print("  Data   : batch yf.download() + static NSE inst. ownership table")
    print("=" * 66)

    # ── STEP 1: Download history for all tickers ─────────────────────────────
    hist_map = await batch_download(symbols)

    # ── STEP 2: Compute risk for each symbol ─────────────────────────────────
    print("[>>] Computing real risk scores from actual market data...\n")

    results = []
    ok_count = 0
    fail_count = 0

    async with httpx.AsyncClient(timeout=20.0) as client:
        for i, symbol in enumerate(symbols, 1):
            snap = build_snapshot(symbol, hist_map)
            assessment = calculate_risk(snap)
            explanation = _build_explanation(symbol, snap, assessment)

            tag  = "[RED]  " if assessment.risk_level == "red" else "[GREEN]"
            vsr  = f"{snap.volume_spike_ratio:.2f}x"         if snap.volume_spike_ratio     else "  N/A "
            std  = f"{snap.daily_return_std:.4f}"            if snap.daily_return_std        else "  N/A "
            chg  = f"{snap.recent_price_change_pct:+.2f}%"  if snap.recent_price_change_pct else "  N/A "
            inst = f"{snap.institutional_ownership_pct:.1f}%" if snap.institutional_ownership_pct else " N/A"

            print(
                f"[{i:2d}/{len(symbols)}] {symbol:<12} {tag} "
                f"score={assessment.risk_score:3d}  "
                f"vol={vsr}  std={std}  3d={chg}  inst={inst}",
                end="",
                flush=True,
            )

            results.append({
                "symbol":  symbol,
                "company": snap.company_name,
                "score":   assessment.risk_score,
                "level":   assessment.risk_level,
                "vol":     snap.volume_spike_ratio,
                "std":     snap.daily_return_std,
                "chg":     snap.recent_price_change_pct,
                "inst":    snap.institutional_ownership_pct,
                "price":   snap.current_price,
            })

            if dry_run:
                print("  [dry-run]")
                ok_count += 1
            else:
                success, action = await upsert_notion_page(
                    client, database_id, symbol, snap, assessment, explanation
                )
                if success:
                    print(f"  [{action}]")
                    ok_count += 1
                else:
                    fail_count += 1

    # ── STEP 3: Summary leaderboard ──────────────────────────────────────────
    print()
    print("=" * 66)
    print(f"  Done!  OK={ok_count}  FAIL={fail_count}")
    print()

    red_stocks   = sorted([r for r in results if r["level"] == "red"],   key=lambda x: -x["score"])
    green_stocks = sorted([r for r in results if r["level"] == "green"], key=lambda x: -x["score"])

    print(f"  [RED]  HIGH RISK ({len(red_stocks)}):")
    if red_stocks:
        for r in red_stocks:
            print(f"    {r['symbol']:<12}  score={r['score']:3d}  {r['company']}")
    else:
        print("    (none)")

    print(f"\n  [GREEN] LOW RISK ({len(green_stocks)}) -- top 10:")
    for r in green_stocks[:10]:
        print(f"    {r['symbol']:<12}  score={r['score']:3d}  {r['company']}")

    print()
    print("  [RANKED] Full leaderboard:")
    w = 66
    print(f"  {'Rank':<5} {'Symbol':<12} {'Score':>5}  {'Vol Spike':>10}  {'Volatility':>10}  {'3d Chg':>8}  {'Inst%':>6}  {'Price (INR)':>12}")
    print("  " + "-" * w)
    for rank, r in enumerate(sorted(results, key=lambda x: -x["score"]), 1):
        vsr  = f"{r['vol']:.2f}x"    if r["vol"]   else "    N/A"
        std  = f"{r['std']:.4f}"     if r["std"]   else "    N/A"
        chg  = f"{r['chg']:+.2f}%"  if r["chg"]   else "   N/A"
        inst = f"{r['inst']:.1f}%"   if r["inst"]  else "  N/A"
        px   = f"INR {r['price']:,.1f}" if r["price"] else "       N/A"
        lbl  = "[R]" if r["level"] == "red" else "   "
        print(f"  {rank:<5} {lbl} {r['symbol']:<12} {r['score']:>5}  {vsr:>10}  {std:>10}  {chg:>8}  {inst:>6}  {px:>12}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real risk evaluator for Nifty 50")
    parser.add_argument("--dry-run", action="store_true", help="Analyse only, skip Notion")
    parser.add_argument("--symbol",  type=str, default=None, help="Single symbol e.g. --symbol TCS")
    args = parser.parse_args()

    if args.symbol:
        target = [args.symbol.strip().upper()]
    else:
        target = list(NIFTY50_META.keys())

    asyncio.run(main(target, dry_run=args.dry_run))
