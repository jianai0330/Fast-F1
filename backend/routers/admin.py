"""
管理员审核接口
鉴权：Header X-Admin-Token（环境变量 ADMIN_TOKEN，默认 f1admin2026）

GET  /admin/posts                   待审核帖子列表
POST /admin/posts/{id}/approve      通过帖子
POST /admin/posts/{id}/reject       拒绝帖子

GET  /admin/comments                待审核评论列表
POST /admin/comments/{id}/approve   通过评论
POST /admin/comments/{id}/reject    拒绝评论

POST /admin/crawl                   触发爬虫 + AI 分析（一键更新资讯）
"""

import os
from fastapi import APIRouter, Header, HTTPException
from models.response import ok, err
from db.database import (
    posts_pending, post_update_status,
    comments_pending, comment_update_status,
    terms_pending, term_review,
)

router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "f1admin2026")


def _auth(token: str | None):
    """校验管理员 Token，失败抛 403"""
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="无权限，请提供正确的 X-Admin-Token")


# ═══════════════════════════════════════════════
# 帖子审核
# ═══════════════════════════════════════════════

@router.get("/posts")
def get_pending_posts(
    page: int = 1,
    page_size: int = 50,
    x_admin_token: str | None = Header(default=None),
):
    """待审核帖子列表"""
    _auth(x_admin_token)
    try:
        posts = posts_pending(page=page, page_size=page_size)
        return ok({"items": posts, "total": len(posts)})
    except Exception as e:
        return err(str(e))


@router.post("/posts/{post_id}/approve")
def approve_post(
    post_id: int,
    x_admin_token: str | None = Header(default=None),
):
    """通过帖子审核，帖子对所有用户可见"""
    _auth(x_admin_token)
    try:
        post_update_status(post_id, "approved")
        return ok({"post_id": post_id, "status": "approved"})
    except Exception as e:
        return err(str(e))


@router.post("/posts/{post_id}/reject")
def reject_post(
    post_id: int,
    x_admin_token: str | None = Header(default=None),
):
    """拒绝帖子，帖子不对外展示"""
    _auth(x_admin_token)
    try:
        post_update_status(post_id, "rejected")
        return ok({"post_id": post_id, "status": "rejected"})
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════
# 评论审核
# ═══════════════════════════════════════════════

@router.get("/comments")
def get_pending_comments(
    page: int = 1,
    page_size: int = 50,
    x_admin_token: str | None = Header(default=None),
):
    """待审核评论列表（含所属帖子标题）"""
    _auth(x_admin_token)
    try:
        comments = comments_pending(page=page, page_size=page_size)
        return ok({"items": comments, "total": len(comments)})
    except Exception as e:
        return err(str(e))


@router.post("/comments/{comment_id}/approve")
def approve_comment(
    comment_id: int,
    x_admin_token: str | None = Header(default=None),
):
    """通过评论，同时更新帖子 comment_count"""
    _auth(x_admin_token)
    try:
        comment_update_status(comment_id, "approved")
        return ok({"comment_id": comment_id, "status": "approved"})
    except Exception as e:
        return err(str(e))


@router.post("/comments/{comment_id}/reject")
def reject_comment(
    comment_id: int,
    x_admin_token: str | None = Header(default=None),
):
    """拒绝评论"""
    _auth(x_admin_token)
    try:
        comment_update_status(comment_id, "rejected")
        return ok({"comment_id": comment_id, "status": "rejected"})
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════
# 爬虫 + AI 分析（拆分接口，支持前端逐条进度）
# ═══════════════════════════════════════════════

@router.post("/crawl")
def trigger_crawl_and_analyze(
    x_admin_token: str | None = Header(default=None),
):
    """兼容旧版：爬取 + 批量分析（最多5条）"""
    _auth(x_admin_token)
    try:
        from services.news_crawler import crawl_and_analyze
        result = crawl_and_analyze()
        return ok(result)
    except Exception as e:
        return err(str(e))


@router.post("/crawl-only")
def trigger_crawl_only(
    x_admin_token: str | None = Header(default=None),
):
    """只爬取，不分析。返回新增条数 + 待分析列表。"""
    _auth(x_admin_token)
    try:
        from services.news_crawler import crawl_all_with_chinese
        from db.database import news_get_unanalyzed
        crawl_result = crawl_all_with_chinese()
        pending = news_get_unanalyzed(limit=20)
        return ok({
            "crawl": crawl_result,
            "pending": [{"id": n["id"], "title": n["title"]} for n in pending],
        })
    except Exception as e:
        return err(str(e))


@router.post("/analyze-one/{news_id}")
def trigger_analyze_one(
    news_id: int,
    force: bool = False,
    x_admin_token: str | None = Header(default=None),
):
    """分析单条新闻。force=true 时强制清除旧分析并重新生成。"""
    _auth(x_admin_token)
    try:
        from db.database import news_get
        from services.news_analyzer import analyze_one
        news = news_get(news_id)
        if not news:
            return err("新闻不存在")
        if news.get("tech_points") and not force:
            return ok({"news_id": news_id, "skipped": True, "msg": "已分析过"})
        if force and news.get("tech_points"):
            from db.database import get_conn
            with get_conn() as conn:
                conn.execute("DELETE FROM news_analysis WHERE news_id=?", (news_id,))
                conn.commit()
        success = analyze_one(news_id, news["title"], news.get("summary", ""), news.get("url", ""))
        return ok({"news_id": news_id, "success": success})
    except Exception as e:
        return err(str(e))


@router.delete("/analyses")
def clear_all_analyses(
    x_admin_token: str | None = Header(default=None),
):
    """清空所有 AI 分析记录（不删新闻），让全部新闻重新触发分析。"""
    _auth(x_admin_token)
    try:
        from db.database import get_conn
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM news_analysis")
            conn.commit()
            return ok({"deleted": cur.rowcount, "msg": "所有分析已清空，用户点击时将重新生成"})
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════
# 术语审核
# ═══════════════════════════════════════════════

@router.get("/terms")
def get_pending_terms(
    x_admin_token: str | None = Header(default=None),
):
    """待审核用户提交术语列表"""
    _auth(x_admin_token)
    try:
        items = terms_pending()
        return ok({"items": items, "total": len(items)})
    except Exception as e:
        return err(str(e))


@router.post("/terms/{term_id}/approve")
def approve_term(
    term_id: int,
    x_admin_token: str | None = Header(default=None),
):
    _auth(x_admin_token)
    term_review(term_id, "approve")
    return ok({"term_id": term_id, "status": "approved"})


@router.post("/terms/{term_id}/reject")
def reject_term(
    term_id: int,
    x_admin_token: str | None = Header(default=None),
):
    _auth(x_admin_token)
    term_review(term_id, "reject")
    return ok({"term_id": term_id, "status": "rejected"})
