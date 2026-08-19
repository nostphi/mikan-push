import os
import json
import requests
import xml.etree.ElementTree as ET

RSS_URL = os.environ.get('RSS_URL')
PUSH_TOKEN = os.environ.get('PUSH_TOKEN')
HISTORY_FILE = 'history.json'

def get_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_pushplus(title, content):
    url = "https://www.pushplus.plus/send"
    payload = {
        "token": PUSH_TOKEN,
        "title": title,
        "content": content
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"Push status: {resp.text}")
    except Exception as e:
        print(f"Failed to push: {e}")

def main():
    if not RSS_URL or not PUSH_TOKEN:
        print("Missing RSS_URL or PUSH_TOKEN")
        return

    # 拉取 Mikan RSS
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(RSS_URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch RSS: {e}")
        return

    # 解析 XML
    root = ET.fromstring(response.content)
    items = root.findall('./channel/item')
    
    if not items:
        print("RSS feed is empty.")
        return

    # 测试模式：直接推送列表里最新的第 1 条番剧
    latest_item = items[0]
    title = latest_item.find('title').text if latest_item.find('title') is not None else '测试推送'
    link = latest_item.find('link').text if latest_item.find('link') is not None else 'https://mikanani.me'
    
    print(f"Testing push for: {title}")
    send_pushplus(f"[测试] {title}", link)

if __name__ == '__main__':
    main()
