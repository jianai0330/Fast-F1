"""
RSS 新闻爬虫
数据源：The Race / Motorsport.com F1
依赖：pip install feedparser
"""

import feedparser
import time
import logging
from db.database import news_insert

logger = logging.getLogger(__name__)

# ── 数据源配置 ──────────────────────────────────
RSS_SOURCES = [
    {
        "name": "The Race",
        "url":  "https://the-race.com/feed/",
        "slug": "the_race",
    },
    {
        "name": "Motorsport.com",
        "url":  "https://www.motorsport.com/rss/f1/news/",
        "slug": "motorsport",
    },
]


def _parse_entry(entry: dict, source_name: str) -> dict | None:
    """解析单条 RSS entry，返回标准化字段；解析失败返回 None"""
    try:
        title = entry.get("title", "").strip()
        url   = entry.get("link", "").strip()
        if not title or not url:
            return None

        # 摘要：优先 summary，其次 content
        summary = ""
        if entry.get("summary"):
            summary = entry["summary"].strip()
        elif entry.get("content"):
            summary = entry["content"][0].get("value", "").strip()
        # 去掉 HTML 标签（简单处理）
        import re
        summary = re.sub(r"<[^>]+>", "", summary)[:500]

        # 发布时间：struct_time → unix timestamp
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = int(time.mktime(pub)) if pub else int(time.time())

        return {
            "title":        title,
            "summary":      summary,
            "url":          url,
            "source":       source_name,
            "published_at": published_at,
        }
    except Exception as e:
        logger.warning(f"解析 RSS entry 失败：{e}")
        return None


def crawl_source(source: dict) -> tuple[int, int]:
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
            item = _parse_entry(entry, source["name"])
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
    爬取所有数据源。
    返回汇总结果：{source_name: {added, skipped}}
    """
    result = {}
    for source in RSS_SOURCES:
        added, skipped = crawl_source(source)
        result[source["name"]] = {"added": added, "skipped": skipped}
        logger.info(f"[{source['name']}] 完成：新增 {added}，跳过 {skipped}")
    return result


def crawl_and_analyze() -> dict:
    """
    爬取 + 触发 AI 分析（供定时任务调用）。
    分析部分由 news_analyzer 模块负责。
    """
    crawl_result = crawl_all()

    # 延迟导入，避免循环依赖
    try:
        from services.news_analyzer import analyze_pending
        analyze_result = analyze_pending(limit=5)
    except Exception as e:
        logger.error(f"AI 分析触发失败：{e}")
        analyze_result = {"error": str(e)}

    return {"crawl": crawl_result, "analyze": analyze_result}
