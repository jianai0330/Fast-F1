"""
术语库接口
GET /terms          — 列表，支持 ?category=&level= 过滤
GET /terms/{slug}   — 单个术语详情
GET /terms/news/{news_id} — 某条新闻匹配的术语标签
"""

from fastapi import APIRouter, HTTPException, Query
from db.database import terms_all, terms_get, terms_by_news

router = APIRouter(prefix="/terms", tags=["terms"])

VALID_CATEGORIES = {"power_unit", "aero", "tyre", "strategy", "rules", "flag"}


@router.get("")
def get_terms(
    category: str | None = Query(None),
    level: int | None = Query(None, ge=1, le=3),
):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(400, f"category 须为 {VALID_CATEGORIES} 之一")
    items = terms_all(category=category, level=level)
    return {"status": "ok", "data": items}


@router.get("/news/{news_id}")
def get_terms_by_news(news_id: int):
    """返回某条新闻匹配到的术语标签列表"""
    items = terms_by_news(news_id)
    return {"status": "ok", "data": items}


@router.get("/{slug}")
def get_term(slug: str):
    item = terms_get(slug)
    if not item:
        raise HTTPException(404, "术语不存在")
    return {"status": "ok", "data": item}
