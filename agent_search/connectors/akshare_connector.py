from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from agent_search.models import MarketBar


@dataclass
class RealtimeQuote:
    symbol: str
    price: float
    change_pct: float
    volume: float
    amount: float


class AkShareConnector:
    """Connector for A-share market data via AkShare."""

    def __init__(self) -> None:
        self.source = "akshare"

    @staticmethod
    def _import_akshare() -> Any:
        try:
            import akshare as ak  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "akshare is required for market data. Install with `pip install akshare`."
            ) from exc
        return ak

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unsupported datetime format: {value}")

    @classmethod
    def map_hist_row(cls, symbol: str, row: dict[str, Any]) -> MarketBar:
        return MarketBar(
            symbol=symbol,
            ts=cls._parse_datetime(row.get("日期")),
            open=float(row.get("开盘", 0.0) or 0.0),
            high=float(row.get("最高", 0.0) or 0.0),
            low=float(row.get("最低", 0.0) or 0.0),
            close=float(row.get("收盘", 0.0) or 0.0),
            volume=float(row.get("成交量", 0.0) or 0.0),
            amount=float(row.get("成交额", 0.0) or 0.0),
            source="akshare",
        )

    def get_kline(
        self,
        symbol: str,
        start: str,
        end: str,
        adjust: str = "qfq",
        period: str = "daily",
    ) -> list[MarketBar]:
        ak = self._import_akshare()
        start_date = start.replace("-", "")
        end_date = end.replace("-", "")
        frame = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if frame is None or frame.empty:
            return []
        bars = [self.map_hist_row(symbol, row) for row in frame.to_dict("records")]
        bars.sort(key=lambda x: x.ts)
        return bars

    def get_realtime_quotes(self, symbols: list[str]) -> dict[str, RealtimeQuote]:
        if not symbols:
            return {}
        symbol_set = set(symbols)
        ak = self._import_akshare()
        frame = ak.stock_zh_a_spot_em()
        if frame is None or frame.empty:
            return {}

        quotes: dict[str, RealtimeQuote] = {}
        for row in frame.to_dict("records"):
            symbol = str(row.get("代码", "")).strip()
            if symbol not in symbol_set:
                continue
            quotes[symbol] = RealtimeQuote(
                symbol=symbol,
                price=float(row.get("最新价", 0.0) or 0.0),
                change_pct=float(row.get("涨跌幅", 0.0) or 0.0),
                volume=float(row.get("成交量", 0.0) or 0.0),
                amount=float(row.get("成交额", 0.0) or 0.0),
            )
        return quotes

    def get_trading_calendar(self, start: str, end: str) -> list[date]:
        ak = self._import_akshare()
        frame = ak.tool_trade_date_hist_sina()
        if frame is None or frame.empty:
            return []

        start_dt = datetime.strptime(start, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end, "%Y-%m-%d").date()

        days: list[date] = []
        for row in frame.to_dict("records"):
            trade_day = row.get("trade_date")
            if trade_day is None:
                continue
            day = self._parse_datetime(trade_day).date()
            if start_dt <= day <= end_dt:
                days.append(day)
        return sorted(days)
