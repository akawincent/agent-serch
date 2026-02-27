import openai
import requests
import json
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Missing environment variable: OPENAI_API_KEY")
if not SERPER_API_KEY:
    raise ValueError("Missing environment variable: SERPER_API_KEY")

client = openai.OpenAI(
    base_url="https://right.codes/codex/v1",
    api_key=OPENAI_API_KEY
)

## Call serper service
def search_serper(query):
    print(f"📡 正在搜索: {query}...")
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    return response.text

# Tool for agent
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_serper",
            "description": "当用户询问实时信息或需要联网查询时，使用此工具查找最新信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，例如 '英伟达今日股价'",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# Chat with agent
def chat_with_agent(prompt, max_rounds=8):
    messages = [{"role": "user", "content": prompt}]

    for round_index in range(max_rounds):
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls or []

        if not tool_calls:
            return response_message.content or ""

        print(f"Agent 第 {round_index + 1} 轮触发工具调用...")
        messages.append(
            {
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in tool_calls
                ],
            }
        )

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            tool_result = ""

            if function_name == "search_serper":
                try:
                    function_args = json.loads(tool_call.function.arguments or "{}")
                    query = function_args.get("query", "")
                    tool_result = search_serper(query) if query else "Error: missing query"
                except Exception as err:
                    tool_result = f"Error calling search_serper: {err}"
            else:
                tool_result = f"Error: unknown tool '{function_name}'"

            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_result,
                }
            )

    return f"Reached max rounds ({max_rounds}) without a final answer."

user_question = "参考东方财富网，同花顺，新浪财经等网站，分析a股沪电股份 \
                2026年2月27日的日k趋势以及这一周的周k趋势，向我整理汇报这只股票的行情。 \
                我的交易策略是波段交易，我已持有300股，成本为20859元，我能接受的最大回撤率是30%，\
                接下来，对下一周两天内的趋势做出预测，给我忠实可靠的投资意见。"
answer = chat_with_agent(user_question)
print("\n")
print("-" * 80)
print("\n")
print(f"🤖 Agent回答: {answer}")
