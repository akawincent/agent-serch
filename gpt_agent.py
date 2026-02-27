import openai
import requests
import json
import os
import re
from datetime import datetime

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

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

## Call serper service
def search_serper(query):
    url = "https://google.serper.dev/search"
    print(f"📡 正在搜索: {query}...")
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    result = response.json()

    organic_results = result.get("organic", [])
    if organic_results:
        print("🌐 搜索结果来源网站:")
        for item in organic_results[:5]:
            link = item.get("link")
            if link:
                print(f"- {link}")
    else:
        print("🌐 未在返回结果中找到可用的来源网站链接。")

    return json.dumps(result, ensure_ascii=False)

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
def chat_with_agent(prompt, max_rounds=10):
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


def generate_brief_title(question):
    title_prompt = (
        "请把用户问题概括成一个中文标题，要求："
        "1) 不超过10个汉字；"
        "2) 只输出标题本身；"
        "3) 不要标点符号。"
    )
    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {"role": "system", "content": title_prompt},
            {"role": "user", "content": question},
        ],
    )
    raw_title = (response.choices[0].message.content or "").strip()
    return raw_title


def sanitize_filename(title):
    cleaned = re.sub(r'[\\/:*?"<>|]', "", title).strip()
    if not cleaned:
        cleaned = "分析结果"
    return cleaned[:10]


def save_result_markdown(question, answer):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    try:
        brief_title = generate_brief_title(question)
    except Exception:
        brief_title = "分析结果"

    filename = f"{sanitize_filename(brief_title)}.md"
    file_path = os.path.join(RESULTS_DIR, filename)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = (
        f"# {sanitize_filename(brief_title)}\n\n"
        f"- 时间: {timestamp}\n\n"
        f"## 用户问题\n\n{question}\n\n"
        f"## Agent回答\n\n{answer}\n"
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path

user_question = "参考东方财富网，同花顺，新浪财经等网站，分析a股沪电股份 \
                从2026年2月24日到2026年2月27日的股价趋势，同时也可以参考其他财经新闻提供的 \
                的市场讯息和相关行业动向，向我整理汇报这只股票的行情。 \
                我的交易策略是波段交易，我已持有300股现货，成本为20859元，我能接受的最大回撤率是20%，\
                我也接受“减仓后再买回”的操作，同时承担回吐博得继续上冲的空间 \
                接下来，对下一周的沪电股份股价趋势做出预测，给我忠实可靠的投资意见。"
answer = chat_with_agent(user_question)
saved_file = save_result_markdown(user_question, answer)
print("\n")
print("-" * 80)
print("\n")
print(f"🤖 Agent回答: {answer}")
print(f"📄 已保存结果到: {saved_file}")
