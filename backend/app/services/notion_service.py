import logging
import re
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.models import Analysis, User

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

REQUIRED_DB_PROPERTIES = {
    "Stock": "title",
    "User": "rich_text",
    "Risk Score": "number",
    "Risk Level": "select",
    "Explanation": "rich_text",
    "Timestamp": "date",
    "Analysis ID": "rich_text",
}


def _normalize_database_id(database_id: str) -> str:
    """Strip dashes/spaces so IDs copied from Notion URLs work."""
    return re.sub(r"[\s-]", "", database_id.strip())


def _notion_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.notion_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def is_notion_configured() -> bool:
    return bool(settings.notion_token and settings.notion_database_id)


def _risk_level_label(level: str) -> str:
    return "Red" if level == "red" else "Green"


async def check_notion_connection() -> dict:
    """Verify Notion token, database access, and required property schema."""
    if not is_notion_configured():
        return {
            "configured": False,
            "connected": False,
            "error": "NOTION_TOKEN and NOTION_DATABASE_ID must be set in backend/.env",
        }

    database_id = _normalize_database_id(settings.notion_database_id)
    url = f"{NOTION_API_BASE}/databases/{database_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=_notion_headers())
            if response.status_code == 401:
                return {
                    "configured": True,
                    "connected": False,
                    "error": "Invalid NOTION_TOKEN — create or refresh your integration token",
                }
            if response.status_code == 404:
                return {
                    "configured": True,
                    "connected": False,
                    "error": "Database not found — check NOTION_DATABASE_ID and share the database with your integration",
                }
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        return {
            "configured": True,
            "connected": False,
            "error": f"Notion API error ({exc.response.status_code}): {body}",
        }
    except Exception as exc:
        return {"configured": True, "connected": False, "error": str(exc)}

    properties = data.get("properties", {})
    missing = [name for name in REQUIRED_DB_PROPERTIES if name not in properties]
    wrong_type = [
        name
        for name, expected in REQUIRED_DB_PROPERTIES.items()
        if name in properties and properties[name].get("type") != expected
    ]

    if missing or wrong_type:
        parts = []
        if missing:
            parts.append(f"missing properties: {', '.join(missing)}")
        if wrong_type:
            parts.append(f"wrong property types: {', '.join(wrong_type)}")
        return {
            "configured": True,
            "connected": False,
            "database_title": data.get("title", [{}])[0].get("plain_text", "Unknown"),
            "error": f"Database schema mismatch — {'; '.join(parts)}",
        }

    title_blocks = data.get("title", [])
    database_title = title_blocks[0].get("plain_text", "Unknown") if title_blocks else "Unknown"
    return {
        "configured": True,
        "connected": True,
        "database_title": database_title,
        "database_id": database_id,
    }


async def sync_analysis_to_notion(analysis: Analysis, user: User) -> None:
    if not is_notion_configured():
        logger.info("Notion credentials not configured — skipping sync for analysis %s", analysis.id)
        return

    database_id = _normalize_database_id(settings.notion_database_id)
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Stock": {"title": [{"text": {"content": analysis.stock_symbol}}]},
            "User": {"rich_text": [{"text": {"content": user.email}}]},
            "Risk Score": {"number": analysis.risk_score},
            "Risk Level": {"select": {"name": _risk_level_label(analysis.risk_level)}},
            "Explanation": {
                "rich_text": [{"text": {"content": analysis.explanation[:2000]}}]
            },
            "Timestamp": {
                "date": {"start": analysis.created_at.isoformat() if analysis.created_at else datetime.now(timezone.utc).isoformat()}
            },
            "Analysis ID": {"rich_text": [{"text": {"content": str(analysis.id)}}]},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{NOTION_API_BASE}/pages",
                json=payload,
                headers=_notion_headers(),
            )
            response.raise_for_status()
            logger.info("Synced analysis %s to Notion", analysis.id)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Failed to sync analysis %s to Notion (%s): %s",
            analysis.id,
            exc.response.status_code,
            exc.response.text[:500],
        )
    except Exception as exc:
        logger.error("Failed to sync analysis %s to Notion: %s", analysis.id, exc)
