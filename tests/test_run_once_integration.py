import json
from datetime import datetime, timedelta

from agent_search.config import AppConfig
from agent_search.connectors.announcement_connector import AnnouncementConnector
from agent_search.engine import TradingResearchAgent
from agent_search.models import MarketBar, NewsItem
from agent_search.storage import SQLiteStore


class FakeMarket:
    def get_kline(self, symbol, start, end, adjust="qfq", period="daily"):
        base = datetime(2026, 1, 1)
        bars = []
        price = 10.0
        for i in range(40):
            price += 0.2
            bars.append(
                MarketBar(
                    symbol=symbol,
                    ts=base + timedelta(days=i),
                    open=price - 0.1,
                    high=price + 0.2,
                    low=price - 0.3,
                    close=price,
                    volume=1_000_000 + i * 10_000,
                    amount=(1_000_000 + i * 10_000) * price,
                    source="fake",
                )
            )
        return bars


class FakeSerper:
    def get_news(self, symbol, since_hours=48):
        return [
            NewsItem(
                id="news1",
                symbol=symbol,
                ts=datetime(2026, 2, 27),
                title="公司中标重大订单",
                url="https://finance.example.com/news1",
                source="finance.example.com",
                sentiment=0,
                relevance=1,
            )
        ]

    def search(self, *args, **kwargs):
        return {
            "organic": [
                {
                    "title": "公告",
                    "link": "https://www.cninfo.com.cn/a/1",
                    "date": "2026-02-27",
                }
            ]
        }

    @staticmethod
    def parse_time(raw, default=None):
        return datetime(2026, 2, 27)


class FakeWecom:
    def __init__(self):
        self.sent = []

    def send_text(self, content, mentioned_list=None):
        self.sent.append(content)
        return {"ok": True}


def test_run_once_outputs(tmp_path) -> None:
    results_dir = tmp_path / "results"
    db_path = tmp_path / "data" / "agent.db"

    config = AppConfig.model_validate(
        {
            "results_dir": str(results_dir),
            "storage": {"db_path": str(db_path)},
        }
    )

    store = SQLiteStore(str(db_path))
    serper = FakeSerper()
    notifier = FakeWecom()
    agent = TradingResearchAgent(
        config=config,
        market_connector=FakeMarket(),
        serper_connector=serper,
        announcement_connector=AnnouncementConnector(serper),
        notifier=notifier,
        store=store,
    )

    result = agent.run_once(symbols=["002463"], equity=1_000_000)
    assert len(result.signals) == 1

    out_json = results_dir / result.date.isoformat() / "signals.json"
    out_md = results_dir / result.date.isoformat() / "daily_report.md"
    assert out_json.exists()
    assert out_md.exists()

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload[0]["symbol"] == "002463"
    assert payload[0]["entry"] is not None
