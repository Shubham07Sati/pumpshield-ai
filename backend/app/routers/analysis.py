import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import Analysis, User
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisHistoryResponse,
    AnalysisResponse,
    AnalysisStatsResponse,
    AnalysisSummary,
    IndicatorAverage,
    IndicatorScore,
    MarketContext,
    PricePoint,
    ScoreBucket,
    SymbolStat,
    TimelinePoint,
)
from app.services.gemini_service import generate_explanation
from app.services.market_data import (
    fetch_market_snapshot,
    fetch_price_series,
    normalize_symbol,
    snapshot_to_context,
)
from app.services.notion_service import sync_analysis_to_notion
from app.services.risk_engine import calculate_risk

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)


def _to_response(analysis: Analysis, market_context: MarketContext | None = None) -> AnalysisResponse:
    indicators = [
        IndicatorScore(**item) if isinstance(item, dict) else item
        for item in (analysis.indicators or [])
    ]
    return AnalysisResponse(
        id=analysis.id,
        stock_symbol=analysis.stock_symbol,
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        explanation=analysis.explanation,
        indicators=indicators,
        created_at=analysis.created_at,
        market_context=market_context,
    )


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    payload: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    symbol = normalize_symbol(payload.symbol)

    try:
        snapshot = fetch_market_snapshot(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Market data fetch failed for %s", symbol)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market data for '{symbol}'. Please try again shortly.",
        ) from exc

    assessment = calculate_risk(snapshot)
    explanation = generate_explanation(snapshot, assessment)

    indicators_data = [
        {"name": i.name, "score": i.score, "max_score": i.max_score, "detail": i.detail}
        for i in assessment.indicators
    ]

    analysis = Analysis(
        user_id=current_user.id,
        stock_symbol=symbol,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        explanation=explanation,
        indicators=indicators_data,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    background_tasks.add_task(sync_analysis_to_notion, analysis, current_user)

    price_series = [PricePoint(**p) for p in fetch_price_series(symbol)]
    context = MarketContext(**snapshot_to_context(snapshot), price_series=price_series)
    return _to_response(analysis, market_context=context)


@router.get("/stats", response_model=AnalysisStatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Analysis)
        .filter(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.asc())
        .all()
    )

    total = len(items)
    red_count = sum(1 for a in items if a.risk_level == "red")
    green_count = total - red_count
    avg_score = round(sum(a.risk_score for a in items) / total, 1) if total else 0.0

    buckets = [
        ScoreBucket(label="0–19", count=0),
        ScoreBucket(label="20–39", count=0),
        ScoreBucket(label="40–59", count=0),
        ScoreBucket(label="60–79", count=0),
        ScoreBucket(label="80–100", count=0),
    ]
    for a in items:
        s = a.risk_score
        if s < 20:
            buckets[0].count += 1
        elif s < 40:
            buckets[1].count += 1
        elif s < 60:
            buckets[2].count += 1
        elif s < 80:
            buckets[3].count += 1
        else:
            buckets[4].count += 1

    timeline = [
        TimelinePoint(
            date=a.created_at.strftime("%Y-%m-%d") if a.created_at else "",
            score=a.risk_score,
            stock_symbol=a.stock_symbol,
            risk_level=a.risk_level,
        )
        for a in items[-20:]
    ]

    symbol_map: dict[str, list[Analysis]] = {}
    for a in items:
        symbol_map.setdefault(a.stock_symbol, []).append(a)

    by_symbol = sorted(
        [
            SymbolStat(
                stock_symbol=sym,
                count=len(group),
                avg_score=round(sum(g.risk_score for g in group) / len(group), 1),
                latest_level=group[-1].risk_level,
                latest_score=group[-1].risk_score,
            )
            for sym, group in symbol_map.items()
        ],
        key=lambda x: x.avg_score,
        reverse=True,
    )[:8]

    indicator_totals: dict[str, list[int]] = {}
    indicator_max: dict[str, int] = {}
    for a in items:
        for ind in a.indicators or []:
            if isinstance(ind, dict):
                name = ind.get("name", "")
                indicator_totals.setdefault(name, []).append(int(ind.get("score", 0)))
                indicator_max[name] = int(ind.get("max_score", 0))

    indicator_averages = [
        IndicatorAverage(
            name=name,
            avg_score=round(sum(scores) / len(scores), 1),
            max_score=indicator_max.get(name, 0),
        )
        for name, scores in indicator_totals.items()
    ]

    return AnalysisStatsResponse(
        total=total,
        red_count=red_count,
        green_count=green_count,
        avg_score=avg_score,
        score_buckets=buckets,
        timeline=timeline,
        by_symbol=by_symbol,
        indicator_averages=indicator_averages,
    )


@router.get("/history", response_model=AnalysisHistoryResponse)
def get_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)
    total = query.count()
    items = query.order_by(Analysis.created_at.desc()).offset(skip).limit(limit).all()
    return AnalysisHistoryResponse(
        items=[AnalysisSummary.model_validate(a) for a in items],
        total=total,
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id)
        .first()
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    context = None
    try:
        snapshot = fetch_market_snapshot(analysis.stock_symbol)
        price_series = [PricePoint(**p) for p in fetch_price_series(analysis.stock_symbol)]
        context = MarketContext(**snapshot_to_context(snapshot), price_series=price_series)
    except Exception:
        logger.warning("Could not refresh market context for analysis %s", analysis_id)

    return _to_response(analysis, market_context=context)


@router.get("/notion-stocks")
async def get_notion_stocks(
    current_user: User = Depends(get_current_user),
):
    from app.services.notion_service import NOTION_API_BASE, _notion_headers, _normalize_database_id, is_notion_configured
    from app.config import settings
    import httpx
    
    if not is_notion_configured():
        return {"items": [], "total": 0}
        
    database_id = _normalize_database_id(settings.notion_database_id)
    url = f"{NOTION_API_BASE}/databases/{database_id}/query"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=_notion_headers())
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            parsed_items = []
            for idx, page in enumerate(results):
                props = page.get("properties", {})
                
                # Stock (title)
                stock_title = props.get("Stock", {}).get("title", [])
                stock = stock_title[0].get("plain_text", "Unknown") if stock_title else "Unknown"
                
                # User
                user_rich = props.get("User", {}).get("rich_text", [])
                user = user_rich[0].get("plain_text", "Unknown") if user_rich else "Unknown"
                
                # Risk Score
                score = props.get("Risk Score", {}).get("number", 0)
                if score is None:
                    score = 0
                
                # Risk Level
                level_sel = props.get("Risk Level", {}).get("select", {})
                level = level_sel.get("name", "green").lower() if level_sel else "green"
                if level not in ["red", "green"]:
                    level = "green"
                
                # Timestamp
                ts_date = props.get("Timestamp", {}).get("date", {})
                ts_str = ts_date.get("start", "") if ts_date else ""
                
                parsed_items.append({
                    "id": idx + 10000,
                    "stock_symbol": stock,
                    "risk_score": score,
                    "risk_level": level,
                    "explanation": f"Synced from Notion (analyzed by {user})",
                    "created_at": ts_str or None
                })
            
            return {
                "items": parsed_items,
                "total": len(parsed_items)
            }
    except Exception as exc:
        logger.error("Failed to query Notion stocks: %s", exc)
        return {"items": [], "total": 0}

