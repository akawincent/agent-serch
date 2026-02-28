from datetime import datetime, timezone

from agent_search.connectors.serper_connector import SerperConnector


def test_source_and_dedupe_key() -> None:
    connector = SerperConnector(api_key="dummy")
    now = datetime(2026, 2, 27, 10, 30, tzinfo=timezone.utc)
    payload = {
        "organic": [
            {
                "title": "沪电股份订单增长",
                "link": "https://www.eastmoney.com/a/123",
                "date": "2026-02-27 10:10:00",
            },
            {
                "title": "沪电股份订单增长(重复)",
                "link": "https://www.eastmoney.com/a/123",
                "date": "2026-02-27 10:50:00",
            },
        ]
    }

    items = connector.build_news_items_from_result("002463", payload, now=now, since_hours=48)
    assert len(items) == 2
    assert items[0].source == "eastmoney.com"

    key1 = connector.dedupe_key(items[0])
    key2 = connector.dedupe_key(items[1])
    assert key1 == key2
