from datetime import date

from agent_search.strategy.risk import (
    calculate_position_size_pct,
    calculate_position_size_shares,
    calculate_risk_state,
    stop_loss_price,
    take_profit_price,
)


def test_position_size_formula_matches_lot_rule() -> None:
    shares = calculate_position_size_shares(
        equity=1_000_000,
        entry=100,
        atr=2,
        risk_per_trade=0.01,
        atr_stop_multiple=1.5,
    )
    assert shares == 3300

    pct = calculate_position_size_pct(
        equity=1_000_000,
        entry=100,
        atr=2,
        risk_per_trade=0.01,
        atr_stop_multiple=1.5,
    )
    assert round(pct, 4) == 0.33


def test_stop_and_take_profit() -> None:
    assert stop_loss_price(entry=10, atr=1, atr_stop_multiple=1.5) == 8.5
    assert take_profit_price(entry=10, atr=1, atr_stop_multiple=1.5) == 13.0


def test_risk_state_drawdown_switch() -> None:
    rs = calculate_risk_state(
        equity=850_000,
        peak_equity=1_000_000,
        max_drawdown_limit=0.15,
        on_date=date(2026, 2, 27),
    )
    assert round(rs.drawdown, 4) == 0.15
    assert rs.allow_new_buy is True

    rs2 = calculate_risk_state(
        equity=840_000,
        peak_equity=1_000_000,
        max_drawdown_limit=0.15,
        on_date=date(2026, 2, 27),
    )
    assert rs2.allow_new_buy is False
