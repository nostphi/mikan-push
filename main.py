import os
import json
import time
import re
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

def parse_anime_title(raw_title):
    # 1. 移除开头所有的方括号/圆括号标签（字幕组信息）
    clean = re.sub(r'^(\s*(\[[^\]]*\]|【[^】]*】|\([^\)]*\))\s*)+', '', raw_title).strip()
    
    # 2. 匹配集数特征：支持 " - 08", "[08]", "【08】", "EP08", "第08集"
    ep_pattern = r'(?:-\s*|\[|【|\bEP|第)?\s*([0-9]{1,3}(?:\.[0-9])?)\s*(?:集|话|話|v\d+)?(?:\]|】)?'
    # 优先匹配常见的 " - 08" 或末尾集数标记
    match = re.search(r'(?:-\s*|EP|第)\s*([0-9]{1,3}(?:\.[0-9])?)\s*(?:集|话|話)?', clean, re.I)
    if not match:
        match = re.search(r'\[\s*([0-9]{1,3}(?:\.[0-9])?)\s*\]', clean)
    
    episode = match.group(1).zfill(2) if match else ""

    # 3. 截取集数前面的番剧名主体
    if match:
        name_part = clean[:match.start()].strip()
    else:
        name_part = clean.split('[')[0].split('(')[0].strip()

    # 4. 如果名字中包含多语言斜杠（例如：中文名 / 日文名 / 英文名），优先提取第一段中文名
    if '/' in name_part:
        name_part = name_part.split('/')[0].strip()
    
    # 去除名字末尾可能残留的连字符或多余符号
    name_part = re.sub(r'[\s\-_]+$', '', name_part).strip()

    # 5. 组合最终标题
    if name_part and episode:
        return f"{name_part} - {episode}"
    elif name_part:
        return name_part
    return raw_title[:80]

def send_pushplus(title, content):
    url = "https://www.pushplus.plus/send"
    
    # 提取 "中文名 - 集数"
    parsed_title = parse_anime_title(title)
    
    # 限制标题长度
    safe_title = (parsed_title[:85] + '...') if len(parsed_title) > 90 else parsed_title
    
    # 正文保留完整原始发布标题与链接
    full_content = f"【完整标题】\n{title}\n\n【详情链接】\n{content}"
    
    payload = {
        "token": PUSH_TOKEN,
        "title": safe_title,
        "content": full_content
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Pushing [{safe_title}]: {resp.text}")
    except Exception as e:
        print(f"Failed to push: {e}")

def main():
    if not RSS_URL or not PUSH_TOKEN:
        print("Missing RSS_URL or PUSH_TOKEN")
        return

    # 1. 读取历史记录
    history = get_history()
    is_first_run = len(history) == 0

    # 2. 拉取 Mikan RSS
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(RSS_URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch RSS: {e}")
        save_history(history)
        return

    # 3. 解析 XML
    root = ET.fromstring(response.content)
    items = root.findall('./channel/item')

    new_items = []
    # 逆序处理，确保按时间先后顺序发送
    for item in reversed(items):
        title = item.find('title').text.strip() if item.find('title') is not None else ''
        link = item.find('link').text.strip() if item.find('link') is not None else ''
        guid_node = item.find('guid')
        guid = guid_node.text.strip() if guid_node is not None else (link or title)

        # 只要这个唯一标识没推送过
        if guid and guid not in history:
            history.append(guid)
            if not is_first_run:
                print(f"Pushing: {title}")
                send_pushplus(title, link)
                # 关键：休眠 2 秒，防止多条连发触发 PushPlus 防刷丢包
                time.sleep(2)
            new_items.append(title)

    # 保留最近 150 条记录
    history = history[-150:]
    save_history(history)
    print(f"Check completed. Found {len(new_items)} new items.")

if __name__ == '__main__':
    main()
