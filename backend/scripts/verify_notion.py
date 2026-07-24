"""Verify Notion audit log integration for PumpShield AI."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.notion_service import check_notion_connection, is_notion_configured


async def main() -> int:
    print("=== PumpShield AI — Notion Integration Check ===\n")

    if not is_notion_configured():
        print("[FAIL] Notion is not configured.")
        print("       Copy backend/.env.example to backend/.env and set:")
        print("         NOTION_TOKEN=<your integration secret>")
        print("         NOTION_DATABASE_ID=<your audit log database id>")
        print("\nSetup guide: see README.md → Notion Audit Log Setup")
        return 1

    result = await check_notion_connection()

    if result.get("connected"):
        print(f"[OK] Connected to Notion database: {result.get('database_title')}")
        print(f"     Database ID: {result.get('database_id')}")
        print("\nNotion audit log is ready. Each stock analysis will sync automatically.")
        return 0

    print(f"[FAIL] {result.get('error', 'Unknown error')}")
    print("\nFix the issue above, then re-run: python scripts/verify_notion.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
