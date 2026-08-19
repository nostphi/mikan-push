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
    
    history = get_history()
    is_first_run = len(history) == 0

    new_items = []
    # 逆序处理，确保按时间先后顺序发送
    for item in reversed(items):
        title = item.find('title').text if item.find('title') is not None else ''
        link = item.find('link').text if item.find('link') is not None else ''
        guid = item.find('guid').text if item.find('guid') is not None else link

        if guid not in history:
            history.append(guid)
            if not is_first_run:
                # 非首次运行时推送新番
                send_pushplus(title, link)
            new_items.append(title)

    # 仅保留最近 150 条历史记录
    history = history[-150:]
    save_history(history)
    print(f"Check completed. Found {len(new_items)} new items.")

if __name__ == '__main__':
    main()
