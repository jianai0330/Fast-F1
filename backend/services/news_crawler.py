"""
RSS 新闻爬虫
数据源：英文 - The Race / Motorsport.com / Crash.net / F1i.com
        中文 - 懂球帝F1 / 虎扑F1赛车 / 微博F1官方（via RSSHub）
依赖：pip install feedparser
"""

import feedparser
import requests
import time
import logging
import re
import os
from bs4 import BeautifulSoup
from db.database import news_insert

logger = logging.getLogger(__name__)

# ── 英文数据源配置 ────────────────────────────────
RSS_SOURCES = [
    {
        "name": "The Race",
        "url":  "https://the-race.com/formula-1/feed/",
        "slug": "the_race",
    },
    {
        "name": "Motorsport.com",
        "url":  "https://www.motorsport.com/rss/f1/news/",
        "slug": "motorsport",
    },
    {
        "name": "Crash.net",
        "url":  "https://www.crash.net/rss/f1",
        "slug": "crash",
    },
    {
        "name": "F1i.com",
        "url":  "https://f1i.com/feed",
        "slug": "f1i",
    },
]

# ── 中文数据源配置（网页爬取方式）────────────────────────────────
ZH_WEB_SOURCES = [
    {
        "name": "新浪F1",
        "url":  "https://sports.sina.com.cn/f1/",
        "slug": "sina_f1",
    },
]


def _parse_entry(entry: dict, source_name: str, language: str = 'en') -> dict | None:
    """解析单条 RSS entry，返回标准化字段；解析失败返回 None"""
    try:
        title = entry.get("title", "").strip()
        url   = entry.get("link", "").strip()
        if not title or not url:
            return None

        # 过滤非 F1 内容（Formula E、IndyCar、MotoGP 等）
        NON_F1_KEYWORDS = [
            'formula e', 'formulae', 'fe ', 'indycar', 'motogp',
            'nascar', 'wec ', 'world endurance', 'rally', 'dtm',
            'supercars', 'imsa', 'extreme e',
        ]
        title_lower = title.lower()
        url_lower = url.lower()
        if any(kw in title_lower or kw in url_lower for kw in NON_F1_KEYWORDS):
            return None

        # 摘要：优先 summary，其次 content
        summary = ""
        if entry.get("summary"):
            summary = entry["summary"].strip()
        elif entry.get("content"):
            summary = entry["content"][0].get("value", "").strip()
        # 去掉 HTML 标签 + 清理常见截断词
        summary = re.sub(r"<[^>]+>", "", summary)
        # 清理 RSS 常见截断词（中英文）
        summary = re.sub(
            r'\s*(keep reading|read more|continue reading|read the full story|继续阅读|查看全文|\.{3,}|…+)\s*$',
            '', summary, flags=re.IGNORECASE
        ).strip()
        summary = summary[:500]

        # 发布时间：struct_time → unix timestamp
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = int(time.mktime(pub)) if pub else int(time.time())

        return {
            "title":        title,
            "summary":      summary,
            "url":          url,
            "source":       source_name,
            "language":     language,
            "published_at": published_at,
        }
    except Exception as e:
        logger.warning(f"解析 RSS entry 失败：{e}")
        return None


def crawl_source(source: dict, language: str = 'en') -> tuple[int, int]:
    """
    爬取单个数据源。
    返回 (新增数量, 跳过数量)
    """
    added = skipped = 0
    try:
        feed = feedparser.parse(source["url"])
        if feed.bozo and not feed.entries:
            logger.warning(f"[{source['name']}] RSS 解析异常：{feed.bozo_exception}")
            return 0, 0

        for entry in feed.entries:
            item = _parse_entry(entry, source["name"], language=language)
            if not item:
                continue
            new_id = news_insert(**item)
            if new_id:
                added += 1
                logger.info(f"[{source['name']}] 新增：{item['title'][:40]}")
            else:
                skipped += 1

    except Exception as e:
        logger.error(f"[{source['name']}] 爬取失败：{e}")

    return added, skipped


def crawl_all() -> dict:
    """
    爬取所有英文数据源。
    返回汇总结果：{source_name: {added, skipped}}
    """
    result = {}
    for source in RSS_SOURCES:
        added, skipped = crawl_source(source, language='en')
        result[source["name"]] = {"added": added, "skipped": skipped}
        logger.info(f"[{source['name']}] 完成：新增 {added}，跳过 {skipped}")
    return result


def crawl_chinese_sources() -> dict:
    """
    爬取中文数据源（网页爬取方式）。
    返回汇总结果：{source_name: {added, skipped}}
    """
    result = {}

    for source in ZH_WEB_SOURCES:
        added = skipped = 0
        try:
            resp = requests.get(
                source["url"],
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                timeout=15
            )
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            links = soup.find_all("a", href=True)
            for a in links:
                href = a["href"]
                title = a.get_text(strip=True)

                # 只要 shtml 链接且标题超过8字
                if "shtml" not in href or len(title) < 8:
                    continue

                # 过滤非 F1 内容
                NON_F1_KW = ['coc', 'rally', 'motogp', '越野', '拉力', 'wrc']
                if any(kw in title.lower() for kw in NON_F1_KW):
                    continue

                # 只保留 F1/方程式 相关
                if 'f1' not in href.lower() and 'f1' not in title.lower() and '方程式' not in title:
                    continue

                # 补全 URL
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = "https://sports.sina.com.cn" + href

                # 从 URL 提取日期作为 published_at
                date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', href)
                if date_match:
                    import datetime
                    dt = datetime.datetime(
                        int(date_match.group(1)),
                        int(date_match.group(2)),
                        int(date_match.group(3))
                    )
                    published_at = int(dt.timestamp())
                else:
                    published_at = int(time.time())

                new_id = news_insert(
                    title=title,
                    summary="",
                    url=href,
                    source=source["name"],
                    language="zh",
                    published_at=published_at,
                )
                if new_id:
                    added += 1
                    logger.info(f"[{source['name']}] 新增：{title[:40]}")
                else:
                    skipped += 1

        except Exception as e:
            logger.error(f"[{source['name']}] 爬取失败：{e}")

        result[source["name"]] = {"added": added, "skipped": skipped}
        logger.info(f"[{source['name']}] 完成：新增 {added}，跳过 {skipped}")

    return result


def crawl_all_with_chinese() -> dict:
    """
    爬取全部数据源（英文 + 中文）。
    返回汇总结果：{source_name: {added, skipped}}
    """
    en_result = crawl_all()
    zh_result = crawl_chinese_sources()
    return {**en_result, **zh_result}


def crawl_and_analyze() -> dict:
    """
    爬取 + 触发 AI 分析（供定时任务调用）。
    分析部分由 news_analyzer 模块负责。
    """
    crawl_result = crawl_all_with_chinese()

    # 延迟导入，避免循环依赖
    try:
        from services.news_analyzer import analyze_pending
        analyze_result = analyze_pending(limit=5)
    except Exception as e:
        logger.error(f"AI 分析触发失败：{e}")
        analyze_result = {"error": str(e)}

    return {"crawl": crawl_result, "analyze": analyze_result}
