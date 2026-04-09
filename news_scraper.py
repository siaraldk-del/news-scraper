import requests
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime, timezone, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
SENT_FILE = "sent_news.json"
KST = timezone(timedelta(hours=9))

RSS_FEEDS = [
    {"name": "🪙 CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "category": "코인"},
    {"name": "🪙 CoinTelegraph", "url": "https://cointelegraph.com/rss", "category": "코인"},
    {"name": "🇰🇷 코인니스", "url": "https://coinness.com/rss", "category": "코인KR"},
    {"name": "🇰🇷 블록미디어", "url": "https://www.blockmedia.co.kr/feed/", "category": "코인KR"},
    {"name": "🌍 Reuters", "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best", "category": "경제"},
    {"name": "🇰🇷 한국경제", "url": "https://www.hankyung.com/feed/all-news", "category": "경제KR"},
    {"name": "🌐 AP News", "url": "https://rsshub.app/apnews/topics/world-news", "category": "세계"},
    {"name": "📱 CryptoPanic", "url": "https://cryptopanic.com/news/rss/", "category": "크립토동향"},
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
