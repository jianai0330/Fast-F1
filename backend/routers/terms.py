from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from db.database import terms_all, terms_get, terms_by_news, term_submit, terms_hot, terms_popular
import time

router = APIRouter(tags=["terms"])

VALID_CATEGORIES = {"power_unit", "aero", "tyre", "strategy", "rules", "driving"}

# terms_by_news 缓存（按 news_id，TTL=10min）
_terms_news_cache: dict = {}

def _tnc_get(news_id: int):
    entry = _terms_news_cache.get(news_id)
    if entry and time.time() - entry["ts"] < 600:
        return entry["data"]
    return None

def _tnc_set(news_id: int, data):
    _terms_news_cache[news_id] = {"ts": time.time(), "data": data}

# terms_all 缓存（TTL=10min）
_terms_all_cache: dict = {}

def _ta_get(key: str):
    entry = _terms_all_cache.get(key)
    if entry and time.time() - entry["ts"] < 600:
        return entry["data"]
    return None

def _ta_set(key: str, data):
    _terms_all_cache[key] = {"ts": time.time(), "data": data}

# 热度统计缓存（TTL=1h）
_hot_cache: dict = {}

def _hot_get():
    entry = _hot_cache.get("hot")
    if entry and time.time() - entry["ts"] < 3600:
        return entry["data"]
    return None

def _hot_set(data):
    _hot_cache["hot"] = {"ts": time.time(), "data": data}


@router.get("")
def get_terms(
    category: str | None = Query(None),
    level: int | None = Query(None, ge=1, le=3),
    scene: str | None = Query(None),
):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(400, f"category 须为 {VALID_CATEGORIES} 之一")
    cache_key = f"{category}:{level}:{scene}"
    cached = _ta_get(cache_key)
    if cached is not None:
        return {"status": "ok", "data": cached}
    items = terms_all(category=category, level=level, scene=scene)
    _ta_set(cache_key, items)
    return {"status": "ok", "data": items}


# 必须在 /{slug} 之前注册，否则 "news"/"hot"/"popular" 会被当成 slug
@router.get("/news/{news_id}")
def get_terms_by_news(news_id: int):
    cached = _tnc_get(news_id)
    if cached is not None:
        return {"status": "ok", "data": cached}
    items = terms_by_news(news_id)
    _tnc_set(news_id, items)
    return {"status": "ok", "data": items}


@router.get("/hot")
def get_terms_hot():
    cached = _hot_get()
    if cached is not None:
        return {"status": "ok", "data": cached}
    data = terms_hot()
    _hot_set(data)
    return {"status": "ok", "data": data}


@router.get("/popular")
def get_terms_popular():
    cached = _hot_get()
    if cached is not None:
        # 从缓存的热度数据中取 TOP5
        sorted_slugs = sorted(cached.items(), key=lambda x: x[1], reverse=True)
        top5 = [slug for slug, _ in sorted_slugs[:5]]
        return {"status": "ok", "data": top5}
    data = terms_popular(top_n=5)
    return {"status": "ok", "data": data}


@router.get("/{slug}")
def get_term(slug: str):
    item = terms_get(slug)
    if not item:
        raise HTTPException(404, "术语不存在")
    return {"status": "ok", "data": item}


class TermSubmitBody(BaseModel):
    name_zh: str
    name_en: str
    short_def: str
    category: str
    openid: str | None = None


@router.post("/submit")
def submit_term(body: TermSubmitBody):
    if not body.name_zh.strip() or not body.short_def.strip():
        raise HTTPException(400, "名称和简介不能为空")
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(400, "分类不合法")
    term_id = term_submit(
        name_zh=body.name_zh.strip(),
        name_en=body.name_en.strip() or body.name_zh.strip(),
        short_def=body.short_def.strip(),
        category=body.category,
        submitted_by=body.openid,
    )
    return {"status": "ok", "data": {"id": term_id}}
