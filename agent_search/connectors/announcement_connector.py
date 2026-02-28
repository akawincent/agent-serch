from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent_search.connectors.serper_connector import SerperConnector
from agent_search.models import NewsItem
from agent_search.utils import stable_hash


class AnnouncementConnector:
    """Announcement connector using cninfo search results from Serper."""

    def __init__(self, serper: SerperConnector):
        self.serper = serper

    def get_announcements(self, symbol: str, since_days: int = 7) -> list[NewsItem]:
        query = f"site:cninfo.com.cn {symbol} 公告"
        result = self.serper.search(query, num=10)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=since_days)

        announcements: list[NewsItem] = []
        for item in result.get("organic", []) or []:
            url = str(item.get("link") or "").strip()
            title = str(item.get("title") or "").strip()
            if not url or not title:
                continue

            ts = self.serper.parse_time(item.get("date"), default=now)
            if ts < cutoff:
                continue

            announcements.append(
                NewsItem(
                    id=stable_hash(f"ann|{symbol}|{url}|{title}"),
                    symbol=symbol,
                    ts=ts,
                    title=title,
                    url=url,
                    source="cninfo",
                    sentiment=0.0,
                    relevance=1.0,
                )
            )
        return announcements
