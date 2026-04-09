import requests
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime, timezone, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KST = timezone(timedelta(hours=9))

RSS_FEEDS = [
    {"name": "🪙 CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "category": "코인"},
    {"name": "🪙 CoinTelegraph", "url": "https://cointelegraph.com/rss", "category": "코인"},
    {"name": "🇰🇷 블록미디어", "url": "https://www.blockmedia.co.kr/feed/", "category": "코인KR"},
    {"name": "🇰🇷 한국경제", "url": "https://www.hankyung.com/feed/all-news", "category": "경제KR"},
]

def fetch_rss(feed):
    articles = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(feed["url"], headers=headers, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//atom:entry", ns)
        for item in items[:5]:
            title_el = item.find("title")
            link_el = item.find("link")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            if not link and link_el is not None:
                link = link_el.get("href", "")
            if title and link:
                articles.append({"title": title, "link": link, "source": feed["name"], "category": feed["category"]})
    except Exception as e:
        print(f"[ERROR] {feed['name']}: {e}")
    return articles

def gemini_summarize(articles):
    if not GEMINI_API_KEY or not articles:
        return ""
    titles = "\n".join([f"[{a['category']}] {a['title']}" for a in articles])
    prompt = f"""다음은 최신 뉴스 헤드라인 목록이야. 이걸 읽고:
1. 시장에 가장 영향이 큰 뉴스 TOP 3를 골라서 한 줄 요약
2. 전체적인 시장 분위기를 한 줄로 정리
3. 코인/선물 트레이더 관점에서 주의할 점 한 줄

형식:
🔥 TOP 3:
1. (요약)
2. (요약)
3. (요약)

📊 시장 분위기: (한 줄)
⚠️ 트레이더 주의: (한 줄)

뉴스 목록:
{titles}"""

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        resp = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}]
        }, timeout=30)
        data = resp.json()
        print(f"[GEMINI RESPONSE] {json.dumps(data, ensure_ascii=False)[:500]}")
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            print(f"[GEMINI ERROR] {data['error']['message']}")
            return ""
        else:
            print(f"[GEMINI UNKNOWN] {data}")
            return ""
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return ""

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=10)

def main():
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    all_articles = []
    for feed in RSS_FEEDS:
        print(f"  크롤링: {feed['name']}...")
        all_articles.extend(fetch_rss(feed))
    if not all_articles:
        print("새 뉴스 없음")
        return

    summary = gemini_summarize(all_articles)
    if summary:
        ai_msg = f"🤖 <b>AI 뉴스 브리핑</b> | {now}\n{'━'*30}\n\n{summary}"
        send_telegram(ai_msg)
        time.sleep(1)

    msg = f"📰 <b>뉴스 스크랩</b> | {now}\n{'━'*30}\n\n"
    for art in all_articles:
        msg += f"• <a href=\"{art['link']}\">{art['title']}</a>\n  <i>{art['source']}</i>\n\n"
        if len(msg) > 3800:
            send_telegram(msg)
            msg = ""
            time.sleep(1)
    if msg:
        send_telegram(msg)
    print(f"전송 완료! {len(all_articles)}건")

if __name__ == "__main__":
    main()
