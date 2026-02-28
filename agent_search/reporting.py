from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from agent_search.models import RiskState, TradeSignal


def ensure_daily_dir(results_dir: str | Path, day: date) -> Path:
    out_dir = Path(results_dir) / day.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_signals_json(output_dir: Path, signals: list[TradeSignal]) -> Path:
    payload = [signal.model_dump(mode="json") for signal in signals]
    output_file = output_dir / "signals.json"
    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_file


def write_daily_markdown(
    output_dir: Path,
    day: date,
    signals: list[TradeSignal],
    risk_state: RiskState,
) -> Path:
    lines: list[str] = []
    lines.append(f"# A股波段信号日报 {day.isoformat()}")
    lines.append("")
    lines.append("## 组合风险状态")
    lines.append("")
    lines.append(f"- 账户权益: {risk_state.equity:.2f}")
    lines.append(f"- 峰值权益: {risk_state.peak_equity:.2f}")
    lines.append(f"- 当前回撤: {risk_state.drawdown:.2%}")
    lines.append(f"- 是否允许新增买入: {'是' if risk_state.allow_new_buy else '否'}")
    lines.append("")
    lines.append("## 交易信号")
    lines.append("")

    if not signals:
        lines.append("- 今日无信号")
    else:
        for signal in signals:
            lines.append(f"### {signal.symbol} - {signal.action}")
            lines.append("")
            lines.append(f"- 分数: {signal.score:.2f}")
            lines.append(f"- 置信度: {signal.confidence:.2f}")
            if signal.entry is not None:
                lines.append(f"- 入场参考: {signal.entry:.2f}")
            if signal.stop_loss is not None:
                lines.append(f"- 止损参考: {signal.stop_loss:.2f}")
            if signal.take_profit is not None:
                lines.append(f"- 止盈参考: {signal.take_profit:.2f}")
            lines.append(f"- 建议仓位占比: {signal.position_size_pct:.2%}")
            lines.append(f"- 低置信度标记: {'是' if signal.low_confidence else '否'}")
            lines.append("- 原因:")
            for reason in signal.reasons[:8]:
                lines.append(f"  - {reason}")
            lines.append("- 证据链接:")
            if signal.evidence_urls:
                for url in signal.evidence_urls:
                    lines.append(f"  - {url}")
            else:
                lines.append("  - 无")
            lines.append("")

    output_file = output_dir / "daily_report.md"
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_file
