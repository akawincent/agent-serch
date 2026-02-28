from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_search.config import AppConfig
from agent_search.models import NewsItem, RiskState, SignalAction, TradeSignal
from agent_search.strategy.factors import compute_technical_score
from agent_search.strategy.risk import (
    calculate_position_size_pct,
    stop_loss_price,
    take_profit_price,
)
from agent_search.utils import clamp

POSITIVE_KEYWORDS = ("中标", "预增", "回购", "增持", "突破", "景气", "订单")
NEGATIVE_KEYWORDS = ("减持", "问询", "下滑", "诉讼", "风险", "亏损", "处罚")


def score_news(news_items: list[NewsItem], announcements: list[NewsItem]) -> tuple[float, list[str]]:
    if not news_items and not announcements:
        return 0.0, ["缺少新闻/公告证据"]

    score = 0.0
    reasons: list[str] = []
    corpus = news_items + announcements
    for item in corpus:
        text = item.title
        if any(key in text for key in POSITIVE_KEYWORDS):
            score += 0.8
            reasons.append(f"正向事件: {text[:24]}")
        if any(key in text for key in NEGATIVE_KEYWORDS):
            score -= 0.8
            reasons.append(f"负向事件: {text[:24]}")

    if corpus:
        score += min(1.0, len(corpus) * 0.05)
        reasons.append(f"新闻覆盖数量: {len(corpus)}")

    return clamp(score + 2.5, 0.0, 5.0), reasons


def map_action(score: float, allow_new_buy: bool, buy_threshold: float, reduce_threshold: float) -> SignalAction:
    if score >= buy_threshold and allow_new_buy:
        return SignalAction.BUY
    if score <= reduce_threshold:
        return SignalAction.REDUCE
    if not allow_new_buy and score >= buy_threshold:
        return SignalAction.HOLD
    return SignalAction.HOLD


def build_trade_signal(
    symbol: str,
    bars,
    news_items: list[NewsItem],
    announcements: list[NewsItem],
    config: AppConfig,
    risk_state: RiskState,
    equity: float,
    ts: datetime | None = None,
) -> TradeSignal:
    technical_score, technical_reasons, snapshot = compute_technical_score(bars)
    news_score, news_reasons = score_news(news_items, announcements)

    score = (
        config.signal.technical_weight * technical_score
        + config.signal.news_weight * news_score
    )
    action = map_action(
        score=score,
        allow_new_buy=risk_state.allow_new_buy,
        buy_threshold=config.signal.buy_threshold,
        reduce_threshold=config.signal.reduce_threshold,
    )

    latest_close = bars[-1].close if bars else None
    atr = snapshot.atr14
    stop_loss = stop_loss_price(latest_close or 0.0, atr, config.risk.atr_stop_multiple) if latest_close else None
    take_profit = take_profit_price(latest_close or 0.0, atr, config.risk.atr_stop_multiple) if latest_close else None

    position_size_pct = (
        calculate_position_size_pct(
            equity=equity,
            entry=latest_close,
            atr=atr,
            risk_per_trade=config.risk.risk_per_trade,
            atr_stop_multiple=config.risk.atr_stop_multiple,
        )
        if latest_close is not None
        else 0.0
    )

    evidence_urls = [item.url for item in (news_items + announcements)[:6]]

    reasons = technical_reasons + news_reasons
    if not risk_state.allow_new_buy:
        reasons.append("组合回撤超过阈值，暂停新增买入")

    low_confidence = len(bars) < 25 or len(evidence_urls) < 2
    confidence = 0.4 + min(0.5, len(evidence_urls) * 0.08)
    confidence += 0.1 if len(bars) >= 60 else 0.0
    confidence = clamp(confidence, 0.0, 1.0)
    if low_confidence:
        confidence = min(confidence, 0.55)

    return TradeSignal(
        id=str(uuid4()),
        symbol=symbol,
        ts=ts or datetime.now(timezone.utc),
        action=action,
        entry=latest_close,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confidence=confidence,
        score=round(score, 4),
        reasons=reasons,
        evidence_urls=evidence_urls,
        position_size_pct=round(position_size_pct, 4),
        low_confidence=low_confidence,
    )
