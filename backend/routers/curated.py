import hashlib
import json
import threading

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from services.link_parser import parse_url
from db.database import (
    curated_insert, curated_list, curated_get, curated_tags,
    curated_reset_analysis, posts_by_curated,
)
from models.response import ok, err

router = APIRouter(prefix="/curated", tags=["curated"])


class SubmitRequest(BaseModel):
    url: str
    tags: list[str] = []
    note: str = ""
    submitted_by: str = ""


@router.post("/submit")
def submit_content(req: SubmitRequest):
    """投稿：解析链接并入库"""
    parsed = parse_url(req.url)
    tags_json = json.dumps(req.tags, ensure_ascii=False) if req.tags else "[]"
    content_id = curated_insert(
        url=parsed["url"],
        title=parsed["title"],
        summary=parsed["summary"],
        cover_image=parsed["cover_image"],
        platform=parsed["platform"],
        content_type=parsed["content_type"],
        tags=tags_json,
        note=req.note,
        submitted_by=req.submitted_by,
        archived_html=parsed["archived_html"],
        snapshot_image=parsed.get("snapshot_image", ""),
        published_at=parsed["published_at"],
    )
    if content_id:
        # 投稿成功后异步触发 AI 分析
        _start_curated_analysis(
            content_id, parsed["title"],
            parsed.get("archived_html", ""), parsed["url"],
            summary=parsed["summary"]
        )
        return {"status": "ok", "data": {"id": content_id, "parsed": parsed}}
    else:
        return {"status": "ok", "data": {"id": None, "message": "已存在相同链接", "parsed": parsed}}


class SubmitManualRequest(BaseModel):
    title: str
    summary: str
    platform: str = "other"
    url: str = ""
    tags: list[str] = []
    note: str = ""
    submitted_by: str = ""


@router.post("/submit-manual")
def submit_manual(req: SubmitManualRequest):
    """手动投稿：无需解析链接，直接输入标题和摘要入库"""
    title = req.title.strip()
    summary = req.summary.strip()
    if not title or not summary:
        return {"status": "error", "message": "标题和摘要不能为空"}

    tags_json = json.dumps(req.tags, ensure_ascii=False) if req.tags else "[]"
    content_url = req.url.strip()
    if not content_url:
        digest = hashlib.sha1(f"{title}\n{summary}".encode("utf-8")).hexdigest()[:16]
        content_url = f"manual://{digest}"

    content_id = curated_insert(
        url=content_url,
        title=title,
        summary=summary,
        cover_image="",
        platform=req.platform,
        content_type="manual",
        archived_html="",
        snapshot_image="",
        published_at=None,
        tags=tags_json,
        note=req.note,
        submitted_by=req.submitted_by,
    )

    if content_id:
        # 触发 AI 分析（用 summary 作为素材）
        _start_curated_analysis(
            content_id, title,
            "", content_url,
            summary=summary
        )
        return {"status": "ok", "data": {"id": content_id}}
    else:
        return {"status": "ok", "data": {"id": None, "message": "已存在相同内容"}}


@router.get("/list")
def list_content(page: int = 1, page_size: int = 20,
                 tag: Optional[str] = None,
                 keyword: Optional[str] = None,
                 platform: Optional[str] = None):
    """分页查询精选列表"""
    items = curated_list(page=page, page_size=page_size, tag=tag, keyword=keyword, platform=platform)
    return {"status": "ok", "data": {"items": items, "page": page, "page_size": page_size}}


@router.get("/tags")
def get_tags():
    """获取所有标签"""
    tags = curated_tags()
    return {"status": "ok", "data": tags}


@router.get("/{content_id}")
def get_content(content_id: int):
    """获取单条详情"""
    item = curated_get(content_id)
    if item:
        return {"status": "ok", "data": item}
    return {"status": "error", "message": "未找到"}


@router.get("/{content_id}/posts")
def get_curated_posts(content_id: int):
    """获取精选内容关联帖子"""
    try:
        posts = posts_by_curated(content_id)
        return ok({"items": posts, "total": len(posts)})
    except Exception as e:
        return err(str(e))


@router.post("/{content_id}/analyze")
def trigger_analyze_curated(content_id: int, force: bool = False):
    """
    触发精选内容 AI 解读（异步）。
    - 已分析且非强制 → 直接返回 already_done
    - force=true → 重置分析状态后重新生成
    - 未分析 → 后台线程异步执行，前端轮询
    """
    try:
        item = curated_get(content_id)
        if not item:
            return err("内容不存在")
        if item.get("analyzed") and not force:
            return ok({"status": "already_done"})
        if force and item.get("analyzed"):
            curated_reset_analysis(content_id)
        _start_curated_analysis(
            content_id, item["title"],
            item.get("archived_html", ""), item.get("url", ""),
            summary=item.get("summary", "")
        )
        return ok({"status": "analyzing"})
    except Exception as e:
        return err(str(e))


def _start_curated_analysis(content_id: int, title: str,
                            archived_html: str, url: str,
                            summary: str = ""):
    """启动后台线程执行精选内容 AI 分析"""
    from services.news_analyzer import analyze_curated_content
    t = threading.Thread(
        target=analyze_curated_content,
        args=(content_id, title, archived_html, url),
        kwargs={"summary": summary},
        daemon=True,
    )
    t.start()
