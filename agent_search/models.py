from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SignalAction(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    REDUCE = "REDUCE"


class MarketBar(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    amount: float = 0.0
    source: str = "unknown"


class NewsItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    symbol: str
    ts: datetime
    title: str
    url: str
    source: str
    sentiment: float = 0.0
    relevance: float = 0.0


class TradeSignal(BaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    id: str
    symbol: str
    ts: datetime
    action: SignalAction
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)
    position_size_pct: float = Field(default=0.0, ge=0.0)
    low_confidence: bool = False


class RiskState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    equity: float
    peak_equity: float
    drawdown: float = Field(default=0.0, ge=0.0)
    allow_new_buy: bool = True


class RunResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    symbols: list[str]
    signals: list[TradeSignal]
    risk_state: RiskState
    output_markdown: str
    output_json: str
    alerts_sent: int = 0


class BacktestResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbols: list[str]
    start: date
    end: date
    benchmark_symbol: str
    total_return: float
    benchmark_return: float
    excess_return: float
    max_drawdown: float
    win_rate: float
    profit_loss_ratio: float
    details: dict[str, Any] = Field(default_factory=dict)
