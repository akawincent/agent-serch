from __future__ import annotations

from dataclasses import dataclass

from agent_search.models import MarketBar
from agent_search.utils import clamp


@dataclass
class TechnicalSnapshot:
    ma5: float | None
    ma10: float | None
    ma20: float | None
    rsi14: float | None
    atr14: float | None
    volume_ratio5: float | None
    breakout20: bool


def moving_average(values: list[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    return sum(values[-window:]) / window


def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None

    gains: list[float] = []
    losses: list[float] = []
    for idx in range(-period, 0):
        delta = closes[idx] - closes[idx - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_atr(bars: list[MarketBar], period: int = 14) -> float | None:
    if len(bars) <= period:
        return None

    tr_values: list[float] = []
    for idx in range(1, len(bars)):
        curr = bars[idx]
        prev = bars[idx - 1]
        tr = max(
            curr.high - curr.low,
            abs(curr.high - prev.close),
            abs(curr.low - prev.close),
        )
        tr_values.append(tr)

    if len(tr_values) < period:
        return None
    return sum(tr_values[-period:]) / period


def volume_ratio(bars: list[MarketBar], window: int = 5) -> float | None:
    if len(bars) < window + 1:
        return None
    latest = bars[-1].volume
    base = sum(item.volume for item in bars[-(window + 1) : -1]) / window
    if base <= 0:
        return None
    return latest / base


def is_breakout_20d(bars: list[MarketBar]) -> bool:
    if len(bars) < 21:
        return False
    latest = bars[-1].close
    prev_high = max(item.high for item in bars[-21:-1])
    return latest > prev_high


def compute_technical_score(bars: list[MarketBar]) -> tuple[float, list[str], TechnicalSnapshot]:
    if not bars:
        snapshot = TechnicalSnapshot(None, None, None, None, None, None, False)
        return 0.0, ["缺少K线数据"], snapshot

    closes = [item.close for item in bars]
    ma5 = moving_average(closes, 5)
    ma10 = moving_average(closes, 10)
    ma20 = moving_average(closes, 20)
    rsi14 = calculate_rsi(closes, 14)
    atr14 = calculate_atr(bars, 14)
    vr5 = volume_ratio(bars, 5)
    breakout20 = is_breakout_20d(bars)

    reasons: list[str] = []
    score = 0.0
    last_close = closes[-1]

    if ma5 is not None and last_close > ma5:
        score += 1.0
        reasons.append("收盘价站上MA5")
    if ma5 is not None and ma10 is not None and ma5 > ma10:
        score += 1.0
        reasons.append("MA5上穿MA10")
    if ma10 is not None and ma20 is not None and ma10 > ma20:
        score += 1.0
        reasons.append("MA10上穿MA20")
    if breakout20:
        score += 1.0
        reasons.append("突破20日高点")
    if vr5 is not None and vr5 > 1.2:
        score += 1.0
        reasons.append("量比放大")

    if rsi14 is not None and rsi14 > 75:
        score -= 0.5
        reasons.append("RSI过热")

    snapshot = TechnicalSnapshot(
        ma5=ma5,
        ma10=ma10,
        ma20=ma20,
        rsi14=rsi14,
        atr14=atr14,
        volume_ratio5=vr5,
        breakout20=breakout20,
    )
    return clamp(score, 0.0, 5.0), reasons, snapshot
