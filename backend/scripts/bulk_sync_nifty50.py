#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulk sync all Nifty 50 stocks to Notion.

Usage (from the backend directory):
    python scripts/bulk_sync_nifty50.py

Optional flags:
    --dry-run       Print analysis results but do NOT push to Notion
    --delay 2       Seconds to wait between Notion API calls (default: 1)
    --symbol INFY   Sync a single symbol only
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# ── Make sure the backend package is importable ──────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.market_data import (
    NIFTY50_YAHOO_MAP,
    _DEMO_SNAPSHOTS,
    fetch_market_snapshot,
)
from app.services.risk_engine import calculate_risk
from app.services.notion_service import (
    NOTION_API_BASE,
    _normalize_database_id,
    _notion_headers,
    is_notion_configured,
)

import httpx

# ── Complete Nifty 50 company name table ─────────────────────────────────────
NIFTY50_COMPANIES: dict[str, str] = {
    "ADANIENT":   "Adani Enterprises Ltd.",
    "ADANIPORTS": "Adani Ports and SEZ Ltd.",
    "APOLLOHOSP": "Apollo Hospitals Enterprise Ltd.",
    "ASIANPAINT": "Asian Paints Ltd.",
    "AXISBANK":   "Axis Bank Ltd.",
    "BAJAJ-AUTO": "Bajaj Auto Ltd.",
    "BAJFINANCE": "Bajaj Finance Ltd.",
    "BAJAJFINSV": "Bajaj Finserv Ltd.",
    "BEL":        "Bharat Electronics Ltd.",
    "BHARTIARTL": "Bharti Airtel Ltd.",
    "CIPLA":      "Cipla Ltd.",
    "COALINDIA":  "Coal India Ltd.",
    "DRREDDY":    "Dr. Reddy's Laboratories Ltd.",
    "EICHERMOT":  "Eicher Motors Ltd.",
    "ETERNAL":    "Eternal Ltd.",
    "GRASIM":     "Grasim Industries Ltd.",
    "HCLTECH":    "HCL Technologies Ltd.",
    "HDFCBANK":   "HDFC Bank Ltd.",
    "HDFCLIFE":   "HDFC Life Insurance Company Ltd.",
    "HEROMOTOCO": "Hero MotoCorp Ltd.",
    "HINDALCO":   "Hindalco Industries Ltd.",
    "HINDUNILVR": "Hindustan Unilever Ltd.",
    "ICICIBANK":  "ICICI Bank Ltd.",
    "INDUSINDBK": "IndusInd Bank Ltd.",
    "INFY":       "Infosys Ltd.",
    "ITC":        "ITC Ltd.",
    "JIOFIN":     "Jio Financial Services Ltd.",
    "JSWSTEEL":   "JSW Steel Ltd.",
    "KOTAKBANK":  "Kotak Mahindra Bank Ltd.",
    "LT":         "Larsen & Toubro Ltd.",
    "M&M":        "Mahindra & Mahindra Ltd.",
    "MARUTI":     "Maruti Suzuki India Ltd.",
    "NTPC":       "NTPC Ltd.",
    "ONGC":       "Oil and Natural Gas Corporation Ltd.",
    "POWERGRID":  "Power Grid Corporation of India Ltd.",
    "RELIANCE":   "Reliance Industries Ltd.",
    "SBILIFE":    "SBI Life Insurance Company Ltd.",
    "SHRIRAMFIN": "Shriram Finance Ltd.",
    "SBIN":       "State Bank of India",
    "SUNPHARMA":  "Sun Pharmaceutical Industries Ltd.",
    "TATACONSUM": "Tata Consumer Products Ltd.",
    "TATAMOTORS": "Tata Motors Ltd.",
    "TATASTEEL":  "Tata Steel Ltd.",
    "TCS":        "Tata Consultancy Services Ltd.",
    "TECHM":      "Tech Mahindra Ltd.",
    "TITAN":      "Titan Company Ltd.",
    "TRENT":      "Trent Ltd.",
    "ULTRACEMCO": "UltraTech Cement Ltd.",
    "WIPRO":      "Wipro Ltd.",
    "NESTLEIND":  "Nestlé India Ltd.",
}

# Risk level → Notion select color
RISK_COLORS = {"Green": "green", "Red": "red"}


def _risk_label(level: str) -> str:
    return "Red" if level == "red" else "Green"


def _build_explanation(symbol: str, snapshot, assessment) -> str:
    """Build a concise explanation string for Notion."""
    level = "HIGH" if assessment.risk_level == "red" else "LOW"
    reasons = [f"• {i.detail}" for i in assessment.indicators if i.score > 0]
    if not reasons:
        reasons = ["• No significant manipulation indicators detected."]
    return (
        f"Risk Score: {assessment.risk_score}/100 ({level} risk)\n\n"
        f"{snapshot.company_name} ({symbol}) — Nifty 50\n\n"
        + "\n".join(reasons)
    )


async def push_to_notion(
    client: httpx.AsyncClient,
    symbol: str,
    snapshot,
    assessment,
    explanation: str,
    database_id: str,
) -> bool:
    """Create a single Notion page for this stock analysis."""
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Stock": {
                "title": [{"text": {"content": symbol}}]
            },
            "User": {
                "rich_text": [{"text": {"content": "bulk-sync / nifty50"}}]
            },
            "Risk Score": {"number": assessment.risk_score},
            "Risk Level": {"select": {"name": _risk_label(assessment.risk_level)}},
            "Explanation": {
                "rich_text": [{"text": {"content": explanation[:2000]}}]
            },
            "Timestamp": {
                "date": {
                    "start": __import__("datetime").datetime.now(
                        __import__("datetime").timezone.utc
                    ).isoformat()
                }
            },
            "Analysis ID": {
                "rich_text": [{"text": {"content": f"bulk-{symbol}"}}]
            },
        },
    }

    try:
        resp = await client.post(
            f"{NOTION_API_BASE}/pages",
            json=payload,
            headers=_notion_headers(),
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        print(f"  ✗ Notion API error ({exc.response.status_code}): {exc.response.text[:200]}")
        return False
    except Exception as exc:
        print(f"  ✗ Notion error: {exc}")
        return False


async def main(symbols: list[str], dry_run: bool, delay: float) -> None:
    if not dry_run and not is_notion_configured():
        print(
            "❌  Notion is not configured.\n"
            "    Set NOTION_TOKEN and NOTION_DATABASE_ID in backend/.env and retry."
        )
        sys.exit(1)

    database_id = _normalize_database_id(settings.notion_database_id) if not dry_run else ""

    print(f"\n{'[DRY RUN] ' if dry_run else ''}PumpShield AI - Nifty 50 Bulk Sync")
    print("-" * 58)
    print(f"  Stocks   : {len(symbols)}")
    print(f"  Notion   : {'skipped (dry-run)' if dry_run else 'enabled'}")
    print(f"  DB ID    : {database_id or '-'}")
    print("-" * 58)
    print()

    ok_count = 0
    fail_count = 0
    results = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i:2d}/{len(symbols)}] {symbol:<12}", end=" ", flush=True)

            # 1. Fetch market data (live → demo fallback)
            try:
                snapshot = fetch_market_snapshot(symbol)
            except Exception as exc:
                print(f"✗ market data failed: {exc}")
                fail_count += 1
                continue

            # 2. Calculate risk score
            assessment = calculate_risk(snapshot)
            explanation = _build_explanation(symbol, snapshot, assessment)

            level_icon = "[RED]  " if assessment.risk_level == "red" else "[GREEN]"
            print(
                f"{level_icon} score={assessment.risk_score:3d}  "
                f"price={str(snapshot.current_price or '?'):>10}  "
                f"{snapshot.company_name[:30]}",
                end="",
            )

            results.append({
                "symbol": symbol,
                "company": snapshot.company_name,
                "score": assessment.risk_score,
                "level": assessment.risk_level,
            })

            # 3. Push to Notion (unless dry-run)
            if dry_run:
                print("  [dry-run]")
                ok_count += 1
            else:
                success = await push_to_notion(
                    client, symbol, snapshot, assessment, explanation, database_id
                )
                if success:
                    print("  [OK] synced")
                    ok_count += 1
                else:
                    fail_count += 1

            # Rate-limit guard
            if i < len(symbols):
                await asyncio.sleep(delay)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("-" * 58)
    print(f"  Done!  OK={ok_count} succeeded   FAIL={fail_count} failed")

    red_stocks  = [r for r in results if r["level"] == "red"]
    green_stocks = [r for r in results if r["level"] == "green"]
    print(f"\n  [RED]  High-risk stocks ({len(red_stocks)}):")
    for r in sorted(red_stocks, key=lambda x: -x["score"]):
        print(f"     {r['symbol']:<12} score={r['score']}")
    print(f"\n  [GREEN] Low-risk stocks ({len(green_stocks)}):")
    for r in sorted(green_stocks, key=lambda x: -x["score"]):
        print(f"     {r['symbol']:<12} score={r['score']}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk sync Nifty 50 to Notion")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Analyse stocks but do NOT write to Notion"
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Seconds between Notion API calls (default: 1)"
    )
    parser.add_argument(
        "--symbol", type=str, default=None,
        help="Sync a single symbol (e.g. --symbol INFY)"
    )
    args = parser.parse_args()

    if args.symbol:
        target_symbols = [args.symbol.strip().upper()]
    else:
        target_symbols = list(NIFTY50_COMPANIES.keys())

    asyncio.run(main(target_symbols, dry_run=args.dry_run, delay=args.delay))
