# SearchAgent

## Intro

`SearchAgent` 是一个基于 LLM + Serper 搜索接口的轻量研究 Agent 示例项目，主要用于：

- 通过 Serper 获取实时网页搜索结果
- 让模型按需触发搜索工具并整合回答
- 将最终问答保存为 Markdown 报告到 `results/` 目录

当前仓库包含两个核心脚本：

- `retrieve.py`：最小化 Serper 检索示例
- `gpt_agent.py`：带工具调用循环的 Agent 主流程（含结果落盘）

## Install

### 1) 环境要求

- Python `>= 3.11`
- 可用的 `OPENAI_API_KEY`
- 可用的 `SERPER_API_KEY`

### 2) 安装依赖

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

如果你不使用 `pip install -e .`，也可以手动安装：

```bash
pip install openai requests
```

### 3) 配置环境变量

```bash
export OPENAI_API_KEY="your_openai_key"
export SERPER_API_KEY="your_serper_key"
```

> 说明：`gpt_agent.py` 会在启动时校验这两个变量，缺失会直接抛错退出。

## Quickstart

### A. 先验证搜索能力

```bash
python retrieve.py
```

默认会搜索 `今年的放假安排`，并打印第一条结果信息。

### B. 运行 Agent 主流程

```bash
python gpt_agent.py
```

脚本会：

1. 使用内置的 `user_question` 发起对话
2. 在模型触发工具调用时执行 `search_serper`
3. 汇总回答并生成中文标题
4. 将结果写入 `results/*.md`

终端会输出最终回答和结果文件路径。

## Project Structure

```text
.
├── gpt_agent.py      # Agent 主流程：工具调用、对话循环、结果落盘
├── retrieve.py       # Serper 接口最小示例
├── pyproject.toml    # 项目元信息与依赖
└── results/          # 自动生成的 Markdown 分析结果
```

## Configuration Notes

- 当前 `gpt_agent.py` 中 OpenAI 客户端使用了固定 `base_url`：
  - `https://right.codes/codex/v1`
- 使用模型：
  - `gpt-5.2`
- 最大工具调用轮数：
  - `max_rounds=10`

如需切换模型或网关地址，请修改 `gpt_agent.py` 中 `openai.OpenAI(...)` 与 `client.chat.completions.create(...)` 的参数。

## Output Format

`results/` 下每个报告大致结构如下：

- 标题（由模型生成并清洗）
- 时间戳
- 用户问题
- Agent 回答

文件名会自动去除非法字符并截断到 10 个字符以内。

## Troubleshooting

- 报错 `Missing environment variable: OPENAI_API_KEY` 或 `SERPER_API_KEY`
  - 检查环境变量是否在当前 shell 生效
- Serper 请求失败（HTTP error）
  - 检查 key 是否有效、网络是否可达 `google.serper.dev`
- 模型调用失败
  - 检查 `OPENAI_API_KEY`、`base_url`、模型名是否可用

## Disclaimer

项目中的金融分析示例仅用于演示工具调用与信息整合流程，不构成任何投资建议。

