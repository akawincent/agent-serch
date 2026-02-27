import requests
import json
import os

def search_internet(query):
    url = "https://google.serper.dev/search"
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("Missing environment variable: SERPER_API_KEY")

    payload = json.dumps({
        "q": query,           
        "hl": "zh-cn",       
        "gl": "cn"            
    })

    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()
    
    return results

query = "今年的放假安排"
search_results = search_internet(query)

# print 
if "organic" in search_results:
    first_result = search_results["organic"][0]
    print(f"搜索关键词: {query}")
    print("-" * 20 + '第一条搜索结果' + "-" * 20)
    print(f"标题: {first_result['title']}")
    print(f"链接: {first_result['link']}")
    print(f"简介: {first_result['snippet']}")
    print(f"详情: {first_result}")
else:
    print("没有找到相关结果。")
