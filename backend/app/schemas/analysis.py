from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)


class IndicatorScore(BaseModel):
    name: str
    score: int
    max_score: int
    detail: str


class AnalysisSummary(BaseModel):
    id: int
    stock_symbol: str
    risk_score: int
    risk_level: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisHistoryResponse(BaseModel):
    items: list[AnalysisSummary]
    total: int


class PricePoint(BaseModel):
    date: str
    close: float
    volume: int | None = None


class MarketContext(BaseModel):
    company_name: str | None = None
    current_price: float | None = None
    volume_spike_ratio: float | None = None
    daily_return_std: float | None = None
    institutional_ownership_pct: float | None = None
    recent_price_change_pct: float | None = None
    market_cap: float | None = None
    avg_volume_3d: float | None = None
    avg_volume_30d: float | None = None
    price_series: list[PricePoint] = []


class AnalysisResponse(BaseModel):
    id: int
    stock_symbol: str
    risk_score: int
    risk_level: str
    explanation: str
    indicators: list[IndicatorScore]
    created_at: datetime
    market_context: MarketContext | None = None

    model_config = {"from_attributes": True}


class SymbolStat(BaseModel):
    stock_symbol: str
    count: int
    avg_score: float
    latest_level: str
    latest_score: int


class TimelinePoint(BaseModel):
    date: str
    score: int
    stock_symbol: str
    risk_level: str


class ScoreBucket(BaseModel):
    label: str
    count: int


class IndicatorAverage(BaseModel):
    name: str
    avg_score: float
    max_score: int


class AnalysisStatsResponse(BaseModel):
    total: int
    red_count: int
    green_count: int
    avg_score: float
    score_buckets: list[ScoreBucket]
    timeline: list[TimelinePoint]
    by_symbol: list[SymbolStat]
    indicator_averages: list[IndicatorAverage]
