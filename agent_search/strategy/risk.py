from __future__ import annotations

import math
from datetime import date

from agent_search.models import RiskState
from agent_search.utils import clamp


def stop_loss_price(entry: float, atr: float | None, atr_stop_multiple: float) -> float | None:
    if atr is None or atr <= 0 or entry <= 0:
        return None
    return max(0.01, entry - atr_stop_multiple * atr)


def take_profit_price(
    entry: float,
    atr: float | None,
    atr_stop_multiple: float,
    reward_multiple: float = 2.0,
) -> float | None:
    if atr is None or atr <= 0 or entry <= 0:
        return None
    return entry + reward_multiple * atr_stop_multiple * atr


def calculate_position_size_shares(
    equity: float,
    entry: float,
    atr: float | None,
    risk_per_trade: float,
    atr_stop_multiple: float,
) -> int:
    if equity <= 0 or entry <= 0 or atr is None or atr <= 0:
        return 0
    risk_budget = equity * risk_per_trade
    per_share_risk = atr_stop_multiple * atr
    if per_share_risk <= 0:
        return 0

    raw_shares = risk_budget / per_share_risk
    lot_aligned = math.floor(raw_shares / 100.0) * 100
    return max(0, int(lot_aligned))


def calculate_position_size_pct(
    equity: float,
    entry: float,
    atr: float | None,
    risk_per_trade: float,
    atr_stop_multiple: float,
) -> float:
    shares = calculate_position_size_shares(
        equity=equity,
        entry=entry,
        atr=atr,
        risk_per_trade=risk_per_trade,
        atr_stop_multiple=atr_stop_multiple,
    )
    if shares <= 0 or equity <= 0:
        return 0.0
    notional = shares * entry
    return clamp(notional / equity, 0.0, 1.0)


def calculate_risk_state(
    equity: float,
    peak_equity: float,
    max_drawdown_limit: float,
    on_date: date,
) -> RiskState:
    peak = max(equity, peak_equity)
    drawdown = 0.0 if peak <= 0 else max(0.0, (peak - equity) / peak)
    allow_new_buy = drawdown <= max_drawdown_limit
    return RiskState(
        date=on_date,
        equity=equity,
        peak_equity=peak,
        drawdown=drawdown,
        allow_new_buy=allow_new_buy,
    )
