from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from agent_search.models import MarketBar, NewsItem, RiskState, TradeSignal
from agent_search.utils import stable_hash


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS market_bars (
                symbol TEXT NOT NULL,
                ts TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                amount REAL NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (symbol, ts, source)
            );

            CREATE TABLE IF NOT EXISTS news_items (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                ts TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                sentiment REAL NOT NULL,
                relevance REAL NOT NULL,
                url_hash TEXT NOT NULL,
                hour_bucket TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_news_url_hour
            ON news_items(url_hash, hour_bucket);

            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                ts TEXT NOT NULL,
                action TEXT NOT NULL,
                entry REAL,
                stop_loss REAL,
                take_profit REAL,
                confidence REAL NOT NULL,
                score REAL NOT NULL,
                reasons TEXT NOT NULL,
                evidence_urls TEXT NOT NULL,
                position_size_pct REAL NOT NULL,
                low_confidence INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS risk_states (
                date TEXT PRIMARY KEY,
                equity REAL NOT NULL,
                peak_equity REAL NOT NULL,
                drawdown REAL NOT NULL,
                allow_new_buy INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                event TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    @staticmethod
    def _hour_bucket(dt: datetime) -> str:
        return dt.strftime("%Y%m%d%H")

    def save_market_bars(self, bars: list[MarketBar]) -> None:
        if not bars:
            return
        rows = [
            (
                bar.symbol,
                bar.ts.isoformat(),
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
                bar.amount,
                bar.source,
            )
            for bar in bars
        ]
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO market_bars
            (symbol, ts, open, high, low, close, volume, amount, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def save_news_items(self, items: list[NewsItem]) -> None:
        if not items:
            return
        rows = []
        now = datetime.utcnow().isoformat()
        for item in items:
            rows.append(
                (
                    item.id,
                    item.symbol,
                    item.ts.isoformat(),
                    item.title,
                    item.url,
                    item.source,
                    item.sentiment,
                    item.relevance,
                    stable_hash(item.url),
                    self._hour_bucket(item.ts),
                    now,
                )
            )
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO news_items
            (id, symbol, ts, title, url, source, sentiment, relevance, url_hash, hour_bucket, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def save_signals(self, signals: list[TradeSignal]) -> None:
        if not signals:
            return
        rows = []
        now = datetime.utcnow().isoformat()
        for signal in signals:
            rows.append(
                (
                    signal.id,
                    signal.symbol,
                    signal.ts.isoformat(),
                    signal.action.value if hasattr(signal.action, "value") else str(signal.action),
                    signal.entry,
                    signal.stop_loss,
                    signal.take_profit,
                    signal.confidence,
                    signal.score,
                    json.dumps(signal.reasons, ensure_ascii=False),
                    json.dumps(signal.evidence_urls, ensure_ascii=False),
                    signal.position_size_pct,
                    1 if signal.low_confidence else 0,
                    now,
                )
            )

        self.conn.executemany(
            """
            INSERT OR REPLACE INTO signals
            (id, symbol, ts, action, entry, stop_loss, take_profit, confidence, score,
            reasons, evidence_urls, position_size_pct, low_confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def save_risk_state(self, risk_state: RiskState) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO risk_states
            (date, equity, peak_equity, drawdown, allow_new_buy, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                risk_state.date.isoformat(),
                risk_state.equity,
                risk_state.peak_equity,
                risk_state.drawdown,
                1 if risk_state.allow_new_buy else 0,
                datetime.utcnow().isoformat(),
            ),
        )
        self.conn.commit()

    def log_event(self, event: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO audit_logs (ts, event, payload) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), event, json.dumps(payload, ensure_ascii=False)),
        )
        self.conn.commit()

    def get_latest_risk_state(self) -> RiskState | None:
        row = self.conn.execute(
            "SELECT date, equity, peak_equity, drawdown, allow_new_buy FROM risk_states ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None

        return RiskState(
            date=date.fromisoformat(row["date"]),
            equity=float(row["equity"]),
            peak_equity=float(row["peak_equity"]),
            drawdown=float(row["drawdown"]),
            allow_new_buy=bool(row["allow_new_buy"]),
        )

    def get_signals_by_date(self, day: date) -> list[dict[str, Any]]:
        prefix = day.isoformat()
        rows = self.conn.execute(
            "SELECT * FROM signals WHERE ts LIKE ? ORDER BY ts ASC",
            (f"{prefix}%",),
        ).fetchall()
        output: list[dict[str, Any]] = []
        for row in rows:
            output.append(
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "ts": row["ts"],
                    "action": row["action"],
                    "entry": row["entry"],
                    "stop_loss": row["stop_loss"],
                    "take_profit": row["take_profit"],
                    "confidence": row["confidence"],
                    "score": row["score"],
                    "reasons": json.loads(row["reasons"]),
                    "evidence_urls": json.loads(row["evidence_urls"]),
                    "position_size_pct": row["position_size_pct"],
                    "low_confidence": bool(row["low_confidence"]),
                }
            )
        return output

    def get_signal_by_id(self, signal_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM signals WHERE id=? LIMIT 1",
            (signal_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "symbol": row["symbol"],
            "ts": row["ts"],
            "action": row["action"],
            "entry": row["entry"],
            "stop_loss": row["stop_loss"],
            "take_profit": row["take_profit"],
            "confidence": row["confidence"],
            "score": row["score"],
            "reasons": json.loads(row["reasons"]),
            "evidence_urls": json.loads(row["evidence_urls"]),
            "position_size_pct": row["position_size_pct"],
            "low_confidence": bool(row["low_confidence"]),
        }

    def get_market_bars(self, symbol: str, start: str, end: str) -> list[MarketBar]:
        rows = self.conn.execute(
            """
            SELECT symbol, ts, open, high, low, close, volume, amount, source
            FROM market_bars
            WHERE symbol=? AND ts BETWEEN ? AND ?
            ORDER BY ts ASC
            """,
            (symbol, start, end),
        ).fetchall()
        bars: list[MarketBar] = []
        for row in rows:
            bars.append(
                MarketBar(
                    symbol=row["symbol"],
                    ts=datetime.fromisoformat(row["ts"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    amount=float(row["amount"]),
                    source=row["source"],
                )
            )
        return bars

    def close(self) -> None:
        self.conn.close()
