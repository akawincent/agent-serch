from __future__ import annotations

import argparse
import json
from datetime import date, datetime

from agent_search.backtest import BacktestEngine
from agent_search.config import load_config, load_watchlist
from agent_search.connectors import AkShareConnector
from agent_search.engine import TradingResearchAgent
from agent_search.scheduler import AgentScheduler


def _split_symbols(raw: str | None, fallback: list[str]) -> list[str]:
    if not raw:
        return fallback
    return [item.strip() for item in raw.split(",") if item.strip()]


def cmd_run_once(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    watchlist = load_watchlist(config.universe_file)
    symbols = _split_symbols(args.symbols, watchlist)

    agent = TradingResearchAgent(config)
    result = agent.run_once(symbols=symbols, equity=args.equity)

    print(f"date={result.date.isoformat()}")
    print(f"symbols={','.join(result.symbols)}")
    print(f"signals={len(result.signals)}")
    print(f"alerts_sent={result.alerts_sent}")
    print(f"json={result.output_json}")
    print(f"markdown={result.output_markdown}")
    return 0


def cmd_run_schedule(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    agent = TradingResearchAgent(config)
    scheduler = AgentScheduler(agent, timezone=config.timezone)
    scheduler.run_forever(equity=args.equity)
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    watchlist = load_watchlist(config.universe_file)
    symbols = _split_symbols(args.symbols, watchlist)
    if not symbols:
        raise SystemExit("No symbols configured. Use --symbols or config/watchlist.csv")

    engine = BacktestEngine(config=config, market_connector=AkShareConnector())
    try:
        result = engine.run(
            symbols=symbols,
            start=args.start,
            end=args.end,
            benchmark_symbol=args.benchmark,
        )
    except Exception as err:  # noqa: BLE001
        print(f"ERROR: backtest failed: {err}")
        return 1
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))

    if result.max_drawdown > config.risk.max_drawdown_limit:
        print("WARNING: max_drawdown exceeded configured limit")
    if result.excess_return <= 0:
        print("WARNING: excess_return is not positive")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    agent = TradingResearchAgent(config)
    target_day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    signals = agent.get_daily_signals(target_day)
    print(json.dumps({"date": target_day.isoformat(), "signals": signals}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-search", description="A-share trading research agent")
    parser.add_argument("--config", default="config/config.yaml", help="config file path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_once = subparsers.add_parser("run-once", help="run one scan cycle")
    run_once.add_argument("--symbols", default="", help="comma separated symbols")
    run_once.add_argument("--equity", type=float, default=1_000_000.0)
    run_once.set_defaults(func=cmd_run_once)

    run_schedule = subparsers.add_parser("run-schedule", help="run scheduler loop")
    run_schedule.add_argument("--equity", type=float, default=1_000_000.0)
    run_schedule.set_defaults(func=cmd_run_schedule)

    backtest = subparsers.add_parser("backtest", help="run historical backtest")
    backtest.add_argument("--symbols", default="", help="comma separated symbols")
    backtest.add_argument("--start", required=True, help="YYYY-MM-DD")
    backtest.add_argument("--end", required=True, help="YYYY-MM-DD")
    backtest.add_argument("--benchmark", default="000300")
    backtest.set_defaults(func=cmd_backtest)

    report = subparsers.add_parser("report", help="view stored daily signals")
    report.add_argument("--date", default="", help="YYYY-MM-DD")
    report.set_defaults(func=cmd_report)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
