from __future__ import annotations

from datetime import datetime

from agent_search.config import AppConfig
from agent_search.connectors.akshare_connector import AkShareConnector
from agent_search.models import BacktestResult
from agent_search.strategy.factors import compute_technical_score


class BacktestEngine:
    def __init__(self, config: AppConfig, market_connector: AkShareConnector):
        self.config = config
        self.market_connector = market_connector

    @staticmethod
    def _daily_returns(closes: list[float]) -> list[float]:
        if len(closes) < 2:
            return []
        returns: list[float] = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            curr = closes[i]
            if prev <= 0:
                returns.append(0.0)
            else:
                returns.append(curr / prev - 1.0)
        return returns

    @staticmethod
    def _max_drawdown(equity_curve: list[float]) -> float:
        peak = float("-inf")
        mdd = 0.0
        for value in equity_curve:
            peak = max(peak, value)
            if peak <= 0:
                continue
            drawdown = (peak - value) / peak
            if drawdown > mdd:
                mdd = drawdown
        return mdd

    def _symbol_strategy_returns(self, symbol: str, start: str, end: str) -> list[float]:
        bars = self.market_connector.get_kline(symbol=symbol, start=start, end=end)
        if len(bars) < 30:
            return []

        closes = [bar.close for bar in bars]
        daily_ret = self._daily_returns(closes)

        position = 0
        strategy_returns: list[float] = []
        for i in range(20, len(bars) - 1):
            window = bars[: i + 1]
            score, _, _ = compute_technical_score(window)
            if score >= self.config.signal.buy_threshold:
                position = 1
            elif score <= self.config.signal.reduce_threshold:
                position = 0
            strategy_returns.append(position * daily_ret[i])

        return strategy_returns

    def run(
        self,
        symbols: list[str],
        start: str,
        end: str,
        benchmark_symbol: str = "000300",
    ) -> BacktestResult:
        series = [self._symbol_strategy_returns(symbol, start, end) for symbol in symbols]
        series = [item for item in series if item]
        if not series:
            raise ValueError("No usable backtest series. Check symbols/date range/data source.")

        min_len = min(len(item) for item in series)
        aligned = [item[-min_len:] for item in series]
        portfolio_returns = [sum(day) / len(aligned) for day in zip(*aligned)]

        equity_curve = [1.0]
        for day_ret in portfolio_returns:
            equity_curve.append(equity_curve[-1] * (1.0 + day_ret))
        total_return = equity_curve[-1] - 1.0

        bench_bars = self.market_connector.get_kline(
            symbol=benchmark_symbol,
            start=start,
            end=end,
            adjust="",
            period="daily",
        )
        bench_closes = [bar.close for bar in bench_bars]
        bench_ret = self._daily_returns(bench_closes)
        if bench_ret:
            bench_curve = [1.0]
            for day_ret in bench_ret[-len(portfolio_returns) :]:
                bench_curve.append(bench_curve[-1] * (1.0 + day_ret))
            benchmark_return = bench_curve[-1] - 1.0
        else:
            benchmark_return = 0.0

        active_returns = [ret for ret in portfolio_returns if abs(ret) > 1e-12]
        wins = [ret for ret in active_returns if ret > 0]
        losses = [ret for ret in active_returns if ret < 0]
        win_rate = (len(wins) / len(active_returns)) if active_returns else 0.0
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
        pl_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        return BacktestResult(
            symbols=symbols,
            start=datetime.strptime(start, "%Y-%m-%d").date(),
            end=datetime.strptime(end, "%Y-%m-%d").date(),
            benchmark_symbol=benchmark_symbol,
            total_return=round(total_return, 6),
            benchmark_return=round(benchmark_return, 6),
            excess_return=round(total_return - benchmark_return, 6),
            max_drawdown=round(self._max_drawdown(equity_curve), 6),
            win_rate=round(win_rate, 6),
            profit_loss_ratio=round(pl_ratio, 6),
            details={
                "days": len(portfolio_returns),
                "active_days": len(active_returns),
                "equity_curve_tail": equity_curve[-5:],
            },
        )
