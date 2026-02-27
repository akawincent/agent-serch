import openai
import requests
import json
import os

# 配置 API Keys
OPENAI_API_KEY = "你的_OPENAI_API_KEY"
SERPER_API_KEY = "你的_SERPER_API_KEY"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- 1. 定义 Serper 搜索函数 ---
def search_serper(query):
    print(f"📡 正在搜索: {query}...")
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text

# --- 2. 定义工具描述 (让 GPT-4 知道如何使用这个函数) ---
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

# --- 3. 模拟对话循环 ---
def chat_with_agent(prompt):
    messages = [{"role": "user", "content": prompt}]
    
    # 第一次对话：把用户意图和工具描述发给 GPT-4
    response = client.chat.completions.create(
        model="gpt-4o", # 或 gpt-4
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # 检查 GPT-4 是否决定调用工具
    if tool_calls:
        # 获取工具名称和参数
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # 执行实际的搜索函数
        if function_name == "search_serper":
            search_result = search_serper(function_args.get("query"))
            
            # 将搜索结果加入消息列表，再次发给 GPT-4
            messages.append(response_message)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": search_result,
                }
            )
            
            # 第二次对话：GPT-4 根据搜索结果生成最终回答
            final_response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )
            return final_response.choices[0].message.content
            
    return response_message.content

# --- 4. 运行示例 ---
user_question = "英伟达现在的股价是多少？"
answer = chat_with_agent(user_question)
print("-" * 20)
print(f"🤖 Agent回答: {answer}")