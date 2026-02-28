from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from agent_search.config import AppConfig, load_watchlist
from agent_search.connectors import (
    AkShareConnector,
    AnnouncementConnector,
    SerperConnector,
    WecomConnector,
)
from agent_search.models import RunResult, SignalAction, TradeSignal
from agent_search.reporting import ensure_daily_dir, write_daily_markdown, write_signals_json
from agent_search.storage import SQLiteStore
from agent_search.strategy import build_trade_signal, calculate_risk_state


class TradingResearchAgent:
    def __init__(
        self,
        config: AppConfig,
        market_connector: AkShareConnector | None = None,
        serper_connector: SerperConnector | None = None,
        announcement_connector: AnnouncementConnector | None = None,
        notifier: WecomConnector | None = None,
        store: SQLiteStore | None = None,
    ) -> None:
        self.config = config
        self.market = market_connector or AkShareConnector()
        self.serper = serper_connector or SerperConnector(
            api_key=os.getenv(config.integrations.serper_api_key_env)
        )
        self.announcements = announcement_connector or AnnouncementConnector(self.serper)
        self.notifier = notifier or WecomConnector(
            webhook_url=os.getenv(config.integrations.wecom_webhook_env)
        )
        self.store = store or SQLiteStore(config.storage.db_path)

    def _default_symbols(self) -> list[str]:
        return load_watchlist(self.config.universe_file)

    def _date_range(self, lookback_days: int = 90) -> tuple[str, str]:
        tz = ZoneInfo(self.config.timezone)
        end_dt = datetime.now(tz).date()
        start_dt = end_dt - timedelta(days=lookback_days)
        return start_dt.isoformat(), end_dt.isoformat()

    def _build_risk_state(self, equity: float, today: date):
        latest = self.store.get_latest_risk_state()
        peak = latest.peak_equity if latest else equity
        return calculate_risk_state(
            equity=equity,
            peak_equity=peak,
            max_drawdown_limit=self.config.risk.max_drawdown_limit,
            on_date=today,
        )

    def _maybe_send_alert(self, signal: TradeSignal) -> bool:
        if signal.action not in (SignalAction.BUY, SignalAction.REDUCE):
            return False
        text = (
            f"[A股信号] {signal.symbol} {signal.action}\n"
            f"score={signal.score:.2f}, confidence={signal.confidence:.2f}\n"
            f"entry={signal.entry}, stop={signal.stop_loss}, take={signal.take_profit}\n"
            f"position={signal.position_size_pct:.2%}\n"
            f"evidence={signal.evidence_urls[0] if signal.evidence_urls else 'N/A'}"
        )
        result = self.notifier.send_text(text)
        self.store.log_event("wecom_alert", {"signal_id": signal.id, "result": result})
        return bool(result.get("ok"))

    def run_once(self, symbols: list[str] | None = None, equity: float = 1_000_000.0) -> RunResult:
        target_symbols = symbols or self._default_symbols()
        if not target_symbols:
            raise ValueError("No symbols provided and watchlist is empty.")

        tz = ZoneInfo(self.config.timezone)
        today = datetime.now(tz).date()
        start, end = self._date_range(lookback_days=120)

        risk_state = self._build_risk_state(equity=equity, today=today)
        self.store.save_risk_state(risk_state)
        self.store.log_event("run_once_start", {"symbols": target_symbols, "date": today.isoformat()})

        all_signals: list[TradeSignal] = []
        alerts_sent = 0

        for symbol in target_symbols:
            low_confidence_reason: str | None = None
            bars = []
            news = []
            announcements = []

            try:
                bars = self.market.get_kline(symbol=symbol, start=start, end=end)
            except Exception as err:  # noqa: BLE001
                low_confidence_reason = f"行情获取失败: {err}"
                self.store.log_event("market_error", {"symbol": symbol, "error": str(err)})

            try:
                news = self.serper.get_news(symbol=symbol, since_hours=48)
            except Exception as err:  # noqa: BLE001
                low_confidence_reason = f"新闻获取失败: {err}"
                self.store.log_event("news_error", {"symbol": symbol, "error": str(err)})

            try:
                announcements = self.announcements.get_announcements(symbol=symbol, since_days=7)
            except Exception as err:  # noqa: BLE001
                low_confidence_reason = f"公告获取失败: {err}"
                self.store.log_event("announcement_error", {"symbol": symbol, "error": str(err)})

            if bars:
                self.store.save_market_bars(bars)
            if news or announcements:
                self.store.save_news_items(news + announcements)

            signal = build_trade_signal(
                symbol=symbol,
                bars=bars,
                news_items=news,
                announcements=announcements,
                config=self.config,
                risk_state=risk_state,
                equity=equity,
                ts=datetime.now(tz),
            )
            if low_confidence_reason:
                signal.low_confidence = True
                signal.reasons.append(low_confidence_reason)

            all_signals.append(signal)

        self.store.save_signals(all_signals)

        for signal in all_signals:
            if self._maybe_send_alert(signal):
                alerts_sent += 1

        out_dir = ensure_daily_dir(self.config.results_dir, today)
        json_file = write_signals_json(out_dir, all_signals)
        md_file = write_daily_markdown(out_dir, today, all_signals, risk_state)

        self.store.log_event(
            "run_once_end",
            {
                "date": today.isoformat(),
                "signals": len(all_signals),
                "alerts_sent": alerts_sent,
                "output": str(out_dir),
            },
        )

        return RunResult(
            date=today,
            symbols=target_symbols,
            signals=all_signals,
            risk_state=risk_state,
            output_markdown=str(md_file),
            output_json=str(json_file),
            alerts_sent=alerts_sent,
        )

    def get_daily_signals(self, day: date):
        return self.store.get_signals_by_date(day)
