import requests
import json

def search_internet(query):
    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": query,           
        "hl": "zh-cn",       
        "gl": "cn"            
    })

    headers = {
        'X-API-KEY': 'e26ef1d0c0b56a5f4b9b17de22cec18cee558123', # 🚨 请替换为你的实际 KEY
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()
    
    return results

query = "2027年春节是哪一天"
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