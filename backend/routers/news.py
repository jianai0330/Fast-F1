"""
资讯接口
GET  /news                      列表（分页，支持 ?team=xxx 过滤）
GET  /news/{id}                 详情（含 AI 三段式）
GET  /news/{id}/teams           该条新闻匹配的车队标签
GET  /news/{id}/posts           关联帖子
GET  /news/{id}/related         关联资讯
POST /news/{id}/analyze-public  任意用户触发 AI 分析（后台异步，结果全局共享）
POST /news/crawl                手动触发爬虫（管理员）
POST /news/{id}/analyze         手动触发单条 AI 分析（管理员）
"""

from fastapi import APIRouter, Header, HTTPException
from models.response import ok, err
from db.database import news_list, news_list_by_team, news_get, posts_by_news, news_delete, news_get_related, news_compute_related
import os
import re
import time
import threading

router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "f1admin2026")

# 车队标签内存缓存（按 news_id，TTL=10min）
_teams_cache: dict = {}

def _teams_cache_get(news_id: int):
    entry = _teams_cache.get(news_id)
    if entry and time.time() - entry["ts"] < 600:
        return entry["data"]
    return None

def _teams_cache_set(news_id: int, data):
    _teams_cache[news_id] = {"ts": time.time(), "data": data}

# 车队关键词映射（slug → 显示名 + 官方色 + 匹配词列表）
TEAMS = {
    "ferrari":      {"name": "法拉利",       "color": "#e8002d", "keywords": ["ferrari", "scuderia ferrari"]},
    "red_bull":     {"name": "红牛",          "color": "#3671c6", "keywords": ["red bull", "red bull racing"]},
    "mercedes":     {"name": "梅赛德斯",      "color": "#27f4d2", "keywords": ["mercedes", "mercedes-amg", "mercedes amg"]},
    "mclaren":      {"name": "迈凯伦",        "color": "#ff8000", "keywords": ["mclaren"]},
    "aston_martin": {"name": "阿斯顿·马丁",  "color": "#229971", "keywords": ["aston martin"]},
    "alpine":       {"name": "阿尔派因",      "color": "#0093cc", "keywords": ["alpine"]},
    "williams":     {"name": "威廉姆斯",      "color": "#64c4ff", "keywords": ["williams"]},
    "racing_bulls": {"name": "Racing Bulls", "color": "#6692ff", "keywords": ["racing bulls", "visa cash app"]},
    "sauber":       {"name": "Audi",          "color": "#52c8c8", "keywords": ["sauber", "audi f1", "stake f1"]},
    "haas":         {"name": "哈斯",          "color": "#b6babd", "keywords": ["haas"]},
    "cadillac":     {"name": "Cadillac",      "color": "#cc0000", "keywords": ["cadillac", "andretti cadillac", "andretti"]},
}


def _teams_from_text(text: str) -> list[dict]:
    """从新闻 title+summary 中匹配车队，返回匹配到的车队列表"""
    t = text.lower()
    result = []
    for slug, info in TEAMS.items():
        if any(re.search(r'\b' + re.escape(kw) + r'\b', t) for kw in info["keywords"]):
            result.append({"slug": slug, "name": info["name"], "color": info["color"]})
    return result


def _check_admin(token: str | None):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="无权限")


# ── 资讯列表 ────────────────────────────────────
@router.get("")
def get_news_list(page: int = 1, page_size: int = 20,
                  team: str | None = None,
                  keyword: str | None = None,
                  language: str = 'all'):
    try:
        if team:
            info = TEAMS.get(team)
            if not info:
                return err(f"未知车队: {team}")
            items = news_list_by_team(info["keywords"], page=page, page_size=page_size, search_keyword=keyword)
        else:
            items = news_list(page=page, page_size=page_size, keyword=keyword,
                              language=language if language != 'all' else None)
        for item in items:
            item["analyzed"] = bool(item.get("analyzed"))
            text = " ".join(filter(None, [item.get("title", ""), item.get("summary", "")]))
            item["teams"] = _teams_from_text(text)
        return ok({"items": items, "page": page, "page_size": page_size})
    except Exception as e:
        return err(str(e))


# ── 车队标签 ─────────────────────────────────────
@router.get("/{news_id}/teams")
def get_news_teams(news_id: int):
    cached = _teams_cache_get(news_id)
    if cached is not None:
        return ok(cached)
    try:
        from db.database import news_get as _get
        item = _get(news_id)
        if not item:
            return err("资讯不存在")
        text = " ".join(filter(None, [item.get("title"), item.get("summary")]))
        result = _teams_from_text(text)
        _teams_cache_set(news_id, result)
        return ok(result)
    except Exception as e:
        return err(str(e))


# ── 资讯详情 ────────────────────────────────────
@router.get("/{news_id}")
def get_news_detail(news_id: int):
    try:
        item = news_get(news_id)
        if not item:
            return err("资讯不存在")
        item["analyzed"] = bool(item.get("tech_points"))
        return ok(item)
    except Exception as e:
        return err(str(e))


# ── 关联帖子列表 ─────────────────────────────────
@router.get("/{news_id}/posts")
def get_news_posts(news_id: int):
    try:
        posts = posts_by_news(news_id)
        return ok({"items": posts, "total": len(posts)})
    except Exception as e:
        return err(str(e))


# ── 关联资讯列表 ────────────────────────────────
@router.get("/{news_id}/related")
def get_related_news(news_id: int, limit: int = 5):
    try:
        items = news_get_related(news_id, limit)
        for item in items:
            item["analyzed"] = bool(item.get("analyzed"))
        return ok({"items": items})
    except Exception as e:
        return err(str(e))


# ── 用户触发 AI 分析（无需登录，结果全局共享）──
@router.post("/{news_id}/analyze-public")
def trigger_analyze_public(news_id: int, force: bool = False):
    """
    任意用户点击「生成 AI 解读」或「重新分析」触发。
    - 已分析且非强制 → 直接返回 already_done，不消耗 token
    - force=true → 删除旧结果重新生成
    - 未分析 → 后台线程异步执行，立即返回 started，前端轮询
    """
    try:
        item = news_get(news_id)
        if not item:
            return err("资讯不存在")
        if item.get("tech_points") and not force:
            return ok({"status": "already_done"})
        if force and item.get("tech_points"):
            from db.database import get_conn
            with get_conn() as conn:
                conn.execute("DELETE FROM news_analysis WHERE news_id=?", (news_id,))
                conn.commit()
        from services.news_analyzer import analyze_one
        t = threading.Thread(
            target=analyze_one,
            args=(news_id, item["title"], item.get("summary", ""), item.get("url", "")),
            daemon=True,
        )
        t.start()
        # 后台触发关联计算
        threading.Thread(
            target=news_compute_related,
            args=(news_id,),
            daemon=True,
        ).start()
        return ok({"status": "started"})
    except Exception as e:
        return err(str(e))


# ── 手动触发爬虫（管理员）───────────────────────
@router.post("/crawl")
def trigger_crawl(x_admin_token: str | None = Header(default=None)):
    _check_admin(x_admin_token)
    try:
        from services.news_crawler import crawl_all_with_chinese
        result = crawl_all_with_chinese()
        return ok(result)
    except Exception as e:
        return err(str(e))


# ── 手动触发单条 AI 分析（管理员）───────────────
@router.post("/{news_id}/analyze")
def trigger_analyze(news_id: int,
                    x_admin_token: str | None = Header(default=None)):
    _check_admin(x_admin_token)
    try:
        item = news_get(news_id)
        if not item:
            return err("资讯不存在")
        if item.get("tech_points"):
            return ok({"msg": "已分析，无需重复", "news_id": news_id})
        from services.news_analyzer import analyze_one
        success = analyze_one(news_id, item["title"], item.get("summary", ""))
        if success:
            return ok({"msg": "分析完成", "news_id": news_id})
        else:
            return err("AI 分析失败，请查看服务端日志")
    except Exception as e:
        return err(str(e))


# ── 删除资讯（管理员）─────────────────────────────
@router.delete("/{news_id}")
def delete_news(news_id: int,
                x_admin_token: str | None = Header(default=None)):
    _check_admin(x_admin_token)
    ok = news_delete(news_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True}
