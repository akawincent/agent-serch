# SearchAgent

## Intro

`SearchAgent` 是一个面向 A 股波段交易的研究型 Agent。它将结构化行情、网页新闻与公告线索整合为可执行交易信号，并提供风险控制、回测和告警能力。

核心目标：在不直接自动下单的前提下，输出更可执行的交易决策支持（入场/止损/仓位/证据链接）。

## Features

- 多源外部交互
- `AkShare`：A 股 K 线、实时行情、交易日历
- `Serper`：财经新闻和网页证据
- `CNINFO`（通过网页检索）：公告线索补充
- `企业微信 Webhook`：高优先级信号告警
- 信号与风控
- 技术因子：`MA5/10/20`、20 日突破、量比、`RSI`、`ATR`
- 事件因子：新闻/公告关键词评分
- 组合风控：最大回撤红线、ATR 止损、风险预算仓位
- 工程能力
- SQLite 持久化（行情、新闻、信号、风险状态、审计日志）
- 结构化输出：`signals.json` + `daily_report.md`
- CLI：`run-once` / `run-schedule` / `backtest` / `report`

## Install

### 1) 环境要求

- Python `>=3.11`

### 2) 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

开发测试环境：

```bash
pip install -e .[dev]
```

### 3) 配置环境变量

```bash
export OPENAI_API_KEY="your_openai_key"
export SERPER_API_KEY="your_serper_key"
export WECOM_WEBHOOK_URL="your_wecom_webhook"
```

## Quickstart

### 1) 配置自选股池

编辑 `config/watchlist.csv`：

```csv
symbol,name
002463,沪电股份
600519,贵州茅台
```

### 2) 运行一次扫描

```bash
python3 -m agent_search.cli run-once --symbols 002463,600519
```

输出文件：

- `results/YYYY-MM-DD/signals.json`
- `results/YYYY-MM-DD/daily_report.md`

### 3) 运行调度模式

```bash
python3 -m agent_search.cli run-schedule --equity 1000000
```

默认调度（见 `config/config.yaml`）：

- 盘前：`09:05`
- 盘中：每 `30` 分钟（9:30-11:30, 13:00-15:00）
- 盘后：`15:10`

### 4) 运行回测

```bash
python3 -m agent_search.cli backtest --start 2023-01-01 --end 2026-02-27 --symbols 002463,600519
```

### 5) 查询某日信号

```bash
python3 -m agent_search.cli report --date 2026-02-27
```

## Project Structure

```text
.
├── agent_search/
│   ├── backtest/            # 回测引擎
│   ├── connectors/          # AkShare/Serper/公告/企业微信连接器
│   ├── storage/             # SQLite 存储
│   ├── strategy/            # 因子、信号、风控
│   ├── cli.py               # CLI 入口
│   ├── config.py            # 配置与自选股加载
│   ├── engine.py            # 运行编排
│   ├── legacy_agent.py      # LLM 工具调用兼容实现
│   ├── reporting.py         # 报告输出
│   └── tools.py             # LLM tool schema 与执行服务
├── config/
│   ├── config.yaml
│   └── watchlist.csv
├── tests/
├── gpt_agent.py             # 兼容入口（转发到 legacy_agent）
└── retrieve.py              # Serper 最小示例
```

## Config

默认配置文件：`config/config.yaml`

```yaml
timezone: Asia/Shanghai
universe_file: config/watchlist.csv
results_dir: results
risk:
  max_drawdown_limit: 0.15
  risk_per_trade: 0.01
  atr_stop_multiple: 1.5
signal:
  technical_weight: 0.7
  news_weight: 0.3
  buy_threshold: 4
  reduce_threshold: 1
storage:
  db_path: data/agent_search.db
```

## Testing

```bash
pytest
```

## Legacy Compatibility

- 旧入口 `gpt_agent.py` 仍可运行。
- 其内部已切换为 `agent_search.legacy_agent`，并支持新的工具接口。

## Disclaimer

本项目用于研究与策略验证，不构成任何投资建议。实盘交易前请自行验证数据质量、策略稳定性与风险承受能力。
