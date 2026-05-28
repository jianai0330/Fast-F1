"""
热门推荐接口

GET  /hot/posts   热门帖子 Top 5
GET  /hot/news    热门资讯 Top 5
"""

import time
from fastapi import APIRouter
from models.response import ok, err
from db.database import get_hot_posts, get_hot_news

router = APIRouter()

# 内存缓存，TTL = 10 分钟
_cache: dict = {}
_CACHE_TTL = 600  # 10 分钟


def _cache_get(key):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None


def _cache_set(key, data):
    _cache[key] = (data, time.time())


@router.get("/posts")
def hot_posts(limit: int = 5):
    """热门帖子 Top N（默认 5），热度分 = (comment_count*0.5 + view_count*0.3) / (hours_since/24 + 1)"""
    cache_key = f"hot_posts_{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return ok(cached)

    try:
        rows = get_hot_posts(limit=limit)
        posts = []
        for r in rows:
            posts.append({
                "id":            r["id"],
                "title":         r["title"],
                "author_name":   r["author_nickname"],
                "comment_count": r["comment_count"],
                "view_count":    r["view_count"],
                "created_at":    r["created_at"],
                "section_name":  r["section_name"],
            })
        result = {"posts": posts}
        _cache_set(cache_key, result)
        return ok(result)
    except Exception as e:
        return err(str(e))


@router.get("/news")
def hot_news(limit: int = 5):
    """热门资讯 Top N（默认 5），有 AI 解读的优先，再按发布时间倒序"""
    cache_key = f"hot_news_{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return ok(cached)

    try:
        rows = get_hot_news(limit=limit)
        news = []
        for r in rows:
            news.append({
                "id":           r["id"],
                "title":        r["title"],
                "source":       r["source"],
                "has_analysis": bool(r["has_analysis"]),
                "published_at": r["published_at"],
            })
        result = {"news": news}
        _cache_set(cache_key, result)
        return ok(result)
    except Exception as e:
        return err(str(e))
