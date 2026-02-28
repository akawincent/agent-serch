from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import openai

from agent_search.config import load_config
from agent_search.tools import ToolService, build_tool_schemas
from agent_search.utils import sanitize_filename


def _build_client() -> openai.OpenAI:
    config = load_config()
    api_key = os.getenv(config.integrations.openai_api_key_env)
    if not api_key:
        raise ValueError(f"Missing environment variable: {config.integrations.openai_api_key_env}")

    return openai.OpenAI(base_url=config.llm.base_url, api_key=api_key)


def _generate_brief_title(client: openai.OpenAI, model: str, question: str) -> str:
    prompt = (
        "请把用户问题概括成一个中文标题，要求："
        "1) 不超过12个汉字；2) 只输出标题本身；3) 不要标点符号。"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
    )
    return (response.choices[0].message.content or "分析报告").strip()


def save_result_markdown(question: str, answer: str, result_dir: str = "results") -> str:
    client = _build_client()
    config = load_config()
    try:
        title = _generate_brief_title(client, config.llm.model, question)
    except Exception:
        title = "分析报告"

    cleaned = sanitize_filename(re.sub(r"\s+", "", title), max_len=20)
    Path(result_dir).mkdir(parents=True, exist_ok=True)
    path = Path(result_dir) / f"{cleaned}.md"

    content = (
        f"# {cleaned}\n\n"
        f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"## 用户问题\n\n{question}\n\n"
        f"## Agent回答\n\n{answer}\n"
    )
    path.write_text(content, encoding="utf-8")
    return str(path)


def chat_with_agent(prompt: str, max_rounds: int | None = None) -> str:
    config = load_config()
    client = _build_client()
    tools = build_tool_schemas()
    tool_service = ToolService(config)
    max_rounds = max_rounds or config.llm.max_rounds

    dispatch: dict[str, Callable[..., Any]] = {
        "get_kline": tool_service.get_kline,
        "get_realtime_quotes": tool_service.get_realtime_quotes,
        "get_news": tool_service.get_news,
        "get_announcements": tool_service.get_announcements,
        "build_signal": tool_service.build_signal,
        "send_wecom_alert": tool_service.send_wecom_alert,
    }

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "你是A股研究助手。必须优先基于工具返回的证据作答，并给出风险提示。"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    for round_idx in range(max_rounds):
        response = client.chat.completions.create(
            model=config.llm.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            return msg.content or ""

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            name = call.function.name
            fn = dispatch.get(name)
            if fn is None:
                payload = {"error": f"unknown tool: {name}"}
            else:
                try:
                    args = json.loads(call.function.arguments or "{}")
                    payload = fn(**args)
                except Exception as err:  # noqa: BLE001
                    payload = {"error": f"tool {name} failed", "detail": str(err)}

            messages.append(
                {
                    "tool_call_id": call.id,
                    "role": "tool",
                    "name": name,
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            )

    return f"Reached max rounds ({max_rounds}) without final answer."


def main() -> None:
    question = (
        "请分析沪电股份最近5个交易日趋势，结合新闻和公告，"
        "给出波段交易建议（含入场、止损、仓位建议）"
    )
    answer = chat_with_agent(question)
    output = save_result_markdown(question, answer)
    print(f"🤖 Agent回答: {answer}")
    print(f"📄 已保存结果到: {output}")


if __name__ == "__main__":
    main()
