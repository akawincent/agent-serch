from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from agent_search.models import NewsItem
from agent_search.utils import source_from_url, stable_hash


class SerperConnector:
    def __init__(self, api_key: str | None = None, base_url: str = "https://google.serper.dev/search"):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = base_url

    def search(self, query: str, num: int = 10, hl: str = "zh-cn", gl: str = "cn") -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing environment variable: SERPER_API_KEY")

        payload = json.dumps({"q": query, "num": num, "hl": hl, "gl": gl})
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(self.base_url, headers=headers, data=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def parse_time(raw: Any, default: datetime | None = None) -> datetime:
        if isinstance(raw, datetime):
            return raw
        default = default or datetime.now(timezone.utc)
        if raw in (None, ""):
            return default

        text = str(raw).strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y/%m/%d %H:%M:%S",
        ):
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return default

    def build_news_items_from_result(
        self,
        symbol: str,
        result: dict[str, Any],
        now: datetime | None = None,
        since_hours: int = 48,
    ) -> list[NewsItem]:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=since_hours)
        items: list[NewsItem] = []
        for item in result.get("organic", []) or []:
            url = str(item.get("link") or "").strip()
            title = str(item.get("title") or "").strip()
            if not url or not title:
                continue

            ts = self.parse_time(item.get("date"), default=now)
            if ts < cutoff:
                continue

            news_item = NewsItem(
                id=stable_hash(f"{symbol}|{url}|{title}"),
                symbol=symbol,
                ts=ts,
                title=title,
                url=url,
                source=source_from_url(url),
                sentiment=0.0,
                relevance=1.0,
            )
            items.append(news_item)
        return items

    @staticmethod
    def dedupe_key(item: NewsItem) -> tuple[str, str]:
        url_hash = stable_hash(item.url)
        hour_bucket = item.ts.astimezone(timezone.utc).strftime("%Y%m%d%H")
        return url_hash, hour_bucket

    def get_news(self, symbol: str, since_hours: int = 48) -> list[NewsItem]:
        query = f"{symbol} A股 最新 新闻 财经"
        result = self.search(query)
        return self.build_news_items_from_result(symbol, result, since_hours=since_hours)
