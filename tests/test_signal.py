from datetime import date, datetime, timedelta

from agent_search.config import AppConfig
from agent_search.models import MarketBar, NewsItem, RiskState, SignalAction
from agent_search.strategy.signal import build_trade_signal


def _bars_uptrend(count: int = 40) -> list[MarketBar]:
    start = datetime(2026, 1, 1)
    bars = []
    price = 10.0
    for i in range(count):
        price += 0.3
        volume = 1_000_000 + i * 20_000
        if i == count - 1:
            volume *= 2.2
        bars.append(
            MarketBar(
                symbol="002463",
                ts=start + timedelta(days=i),
                open=price - 0.2,
                high=price,
                low=price - 0.4,
                close=price,
                volume=volume,
                amount=volume * price,
                source="test",
            )
        )
    return bars


def _bars_downtrend(count: int = 40) -> list[MarketBar]:
    start = datetime(2026, 1, 1)
    bars = []
    price = 30.0
    for i in range(count):
        price -= 0.3
        bars.append(
            MarketBar(
                symbol="002463",
                ts=start + timedelta(days=i),
                open=price + 0.2,
                high=price + 0.4,
                low=price - 0.4,
                close=max(price, 1.0),
                volume=1_000_000 - i * 8_000,
                amount=(1_000_000 - i * 8_000) * max(price, 1.0),
                source="test",
            )
        )
    return bars


def test_signal_buy_mapping() -> None:
    config = AppConfig()
    risk = RiskState(
        date=date(2026, 2, 27),
        equity=1_000_000,
        peak_equity=1_000_000,
        drawdown=0,
        allow_new_buy=True,
    )
    news = [
        NewsItem(
            id="n1",
            symbol="002463",
            ts=datetime(2026, 2, 27),
            title="公司中标新项目且订单增长",
            url="https://finance.example.com/a",
            source="finance.example.com",
            sentiment=0,
            relevance=1,
        )
    ]

    signal = build_trade_signal(
        symbol="002463",
        bars=_bars_uptrend(),
        news_items=news,
        announcements=[],
        config=config,
        risk_state=risk,
        equity=1_000_000,
    )
    assert signal.action == SignalAction.BUY
    assert signal.entry is not None
    assert signal.stop_loss is not None


def test_signal_reduce_mapping() -> None:
    config = AppConfig.model_validate(
        {
            "signal": {
                "technical_weight": 1.0,
                "news_weight": 0.0,
                "buy_threshold": 4,
                "reduce_threshold": 1,
            }
        }
    )
    risk = RiskState(
        date=date(2026, 2, 27),
        equity=1_000_000,
        peak_equity=1_000_000,
        drawdown=0,
        allow_new_buy=True,
    )

    signal = build_trade_signal(
        symbol="002463",
        bars=_bars_downtrend(),
        news_items=[],
        announcements=[],
        config=config,
        risk_state=risk,
        equity=1_000_000,
    )
    assert signal.action == SignalAction.REDUCE
