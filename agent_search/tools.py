from __future__ import annotations

from datetime import date, timedelta

from agent_search.config import AppConfig
from agent_search.engine import TradingResearchAgent


def build_tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_kline",
                "description": "获取A股历史K线数据",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "start": {"type": "string", "description": "YYYY-MM-DD"},
                        "end": {"type": "string", "description": "YYYY-MM-DD"},
                        "adjust": {"type": "string", "default": "qfq"},
                    },
                    "required": ["symbol", "start", "end"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_realtime_quotes",
                "description": "获取A股实时行情",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["symbols"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_news",
                "description": "获取个股相关新闻",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "since_hours": {"type": "integer", "default": 48},
                    },
                    "required": ["symbol"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_announcements",
                "description": "获取个股公告线索",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "since_days": {"type": "integer", "default": 7},
                    },
                    "required": ["symbol"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "build_signal",
                "description": "生成个股交易信号",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "equity": {"type": "number", "default": 1000000},
                    },
                    "required": ["symbol"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_wecom_alert",
                "description": "发送企业微信提醒",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "signal_id": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["signal_id"],
                },
            },
        },
    ]


class ToolService:
    def __init__(self, config: AppConfig) -> None:
        self.agent = TradingResearchAgent(config)

    def get_kline(self, symbol: str, start: str, end: str, adjust: str = "qfq"):
        bars = self.agent.market.get_kline(symbol=symbol, start=start, end=end, adjust=adjust)
        return [bar.model_dump(mode="json") for bar in bars]

    def get_realtime_quotes(self, symbols: list[str]):
        quotes = self.agent.market.get_realtime_quotes(symbols)
        return {symbol: quote.__dict__ for symbol, quote in quotes.items()}

    def get_news(self, symbol: str, since_hours: int = 48):
        items = self.agent.serper.get_news(symbol=symbol, since_hours=since_hours)
        return [item.model_dump(mode="json") for item in items]

    def get_announcements(self, symbol: str, since_days: int = 7):
        items = self.agent.announcements.get_announcements(symbol=symbol, since_days=since_days)
        return [item.model_dump(mode="json") for item in items]

    def build_signal(self, symbol: str, equity: float = 1_000_000.0):
        result = self.agent.run_once(symbols=[symbol], equity=equity)
        if not result.signals:
            return {}
        return result.signals[0].model_dump(mode="json")

    def send_wecom_alert(self, signal_id: str, content: str | None = None):
        signal = self.agent.store.get_signal_by_id(signal_id)
        if signal is None and not content:
            return {"ok": False, "error": f"signal not found: {signal_id}"}

        body = content
        if body is None and signal is not None:
            body = (
                f"[A股信号提醒] {signal['symbol']} {signal['action']}\n"
                f"score={signal['score']:.2f}, confidence={signal['confidence']:.2f}\n"
                f"entry={signal['entry']}, stop={signal['stop_loss']}, take={signal['take_profit']}\n"
                f"position={signal['position_size_pct']:.2%}"
            )
        return self.agent.notifier.send_text(body or "")


def default_date_range(days: int = 60) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()
