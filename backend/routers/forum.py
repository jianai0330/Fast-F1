"""
论坛接口（用户 / 分区 / 帖子 / 评论）

POST /forum/users/register          注册或更新昵称
GET  /forum/users/me                获取用户信息

GET  /forum/sections                所有分区列表

GET  /forum/posts                   帖子列表（?section_id=&page=）
GET  /forum/posts/{id}              帖子详情
POST /forum/posts                   发帖

GET  /forum/posts/{id}/comments     评论列表
POST /forum/posts/{id}/comments     发评论（支持回复 parent_id）

POST /forum/comments/{id}/like      评论点赞/取消
GET  /forum/comments/{id}/like      评论点赞数据
"""

import os
import re
import time
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from models.response import ok, err
from db.database import (
    user_get, user_upsert,
    sections_all,
    post_create, post_list, post_get, post_delete,
    post_like, post_like_counts,
    comment_create, comment_list,
    comment_like, comment_like_counts,
    get_hot_posts,
)

router = APIRouter()

# sections 内存缓存（变化极少，TTL=1h）
_sections_cache: dict = {}

def _sections_cache_get():
    entry = _sections_cache.get("sections")
    if entry and time.time() - entry["ts"] < 3600:
        return entry["data"]
    return None

def _sections_cache_set(data):
    _sections_cache["sections"] = {"ts": time.time(), "data": data}


# 微信 AppID / AppSecret（从环境变量读取）
WX_APPID  = os.getenv("WX_APPID",  "wx8198848f733aa5b2")
WX_SECRET = os.getenv("WX_SECRET", "")


# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════

def _code2openid(code: str) -> str | None:
    """用 wx.login code 换取 openid（避免 AppSecret 暴露在前端）"""
    if not WX_SECRET:
        return f"dev_{code}"
    try:
        url = (
            f"https://api.weixin.qq.com/sns/jscode2session"
            f"?appid={WX_APPID}&secret={WX_SECRET}"
            f"&js_code={code}&grant_type=authorization_code"
        )
        resp = httpx.get(url, timeout=5)
        data = resp.json()
        return data.get("openid")
    except Exception:
        return None


def _valid_nickname(nickname: str) -> bool:
    nickname = nickname.strip()
    if not (2 <= len(nickname) <= 12):
        return False
    if re.search(r'[<>&"\'/\\]', nickname):
        return False
    return True


# ═══════════════════════════════════════════════
# 用户接口
# ═══════════════════════════════════════════════

class RegisterBody(BaseModel):
    code:       str
    nickname:   str
    avatar_url: str = ""


class UpdateNicknameBody(BaseModel):
    openid:   str
    nickname: str


@router.post("/users/update-nickname")
def update_nickname(body: UpdateNicknameBody):
    if not _valid_nickname(body.nickname):
        return err("昵称需 2-12 字，不含特殊符号")
    user = user_upsert(body.openid, body.nickname.strip(), "")
    return ok(user)


@router.post("/users/register")
def register_user(body: RegisterBody):
    if not _valid_nickname(body.nickname):
        return err("昵称需 2-12 字，不含特殊符号")
    openid = _code2openid(body.code)
    if not openid:
        return err("微信登录失败，请重试")
    user = user_upsert(openid, body.nickname.strip(), body.avatar_url)
    return ok(user)


@router.get("/users/me")
def get_user(openid: str):
    user = user_get(openid)
    if not user:
        return err("用户不存在，请先注册")
    return ok(user)


# ═══════════════════════════════════════════════
# 分区接口
# ═══════════════════════════════════════════════

@router.get("/sections")
def get_sections():
    cached = _sections_cache_get()
    if cached:
        return ok(cached)
    try:
        sections = sections_all()
        race_sections = [s for s in sections if s["type"] == "race"]
        team_sections = [s for s in sections if s["type"] == "team"]
        result = {"race": race_sections, "team": team_sections}
        _sections_cache_set(result)
        return ok(result)
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════
# 帖子接口
# ═══════════════════════════════════════════════

class PostBody(BaseModel):
    section_id: int
    title:      str
    content:    str
    openid:     str
    news_id:    int | None = None
    curated_id: int | None = None


@router.get("/posts")
def get_posts(section_id: int | None = None, page: int = 1, page_size: int = 20,
              sort: str = "latest"):
    if sort not in ("latest", "hot"):
        return err("sort 只支持 latest 或 hot")
    try:
        if sort == "hot":
            all_posts = get_hot_posts(limit=page * page_size, section_id=section_id)
            offset = (page - 1) * page_size
            items = all_posts[offset:offset + page_size]
            return ok({"items": items, "page": page, "page_size": page_size})
        else:
            posts = post_list(
                section_id=section_id,
                status="approved",
                page=page,
                page_size=page_size,
            )
            return ok({"items": posts, "page": page, "page_size": page_size})
    except Exception as e:
        return err(str(e))


@router.get("/posts/{post_id}")
def get_post(post_id: int):
    try:
        post = post_get(post_id)
        if not post:
            return err("帖子不存在")
        if post["status"] != "approved" and not post["is_seeded"]:
            return err("帖子不存在或审核中")
        return ok(post)
    except Exception as e:
        return err(str(e))


@router.post("/posts")
def create_post(body: PostBody):
    try:
        user = user_get(body.openid)
        if not user:
            return err("请先设置昵称再发帖")
        title   = body.title.strip()
        content = body.content.strip()
        if not title or len(title) > 50:
            return err("标题不能为空，且不超过 50 字")
        if not content or len(content) > 2000:
            return err("内容不能为空，且不超过 2000 字")
        post_id = post_create(
            section_id      = body.section_id,
            title           = title,
            content         = content,
            author_openid   = body.openid,
            author_nickname = user["nickname"],
            is_seeded       = False,
            news_id         = body.news_id,
            curated_id      = body.curated_id,
        )
        return ok({"post_id": post_id, "msg": "发帖成功！"})
    except Exception as e:
        return err(str(e))


class DeletePostBody(BaseModel):
    openid: str

@router.delete("/posts/{post_id}")
def delete_post(post_id: int, body: DeletePostBody):
    try:
        success = post_delete(post_id, body.openid)
        if not success:
            return err("删除失败，帖子不存在或无权限")
        return ok({"msg": "已删除"})
    except Exception as e:
        return err(str(e))


# ── 点赞 / 点踩 ──────────────────────────────────

class LikeBody(BaseModel):
    openid: str
    type:   str   # "like" | "dislike"

@router.post("/posts/{post_id}/like")
def like_post(post_id: int, body: LikeBody):
    if body.type not in ("like", "dislike"):
        return err("type 必须是 like 或 dislike")
    try:
        result = post_like(post_id, body.openid, body.type)
        return ok(result)
    except Exception as e:
        return err(str(e))

@router.get("/posts/{post_id}/like")
def get_like(post_id: int, openid: str | None = None):
    try:
        result = post_like_counts(post_id, openid)
        return ok(result)
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════
# 评论接口
# ═══════════════════════════════════════════════

class CommentBody(BaseModel):
    content:   str
    openid:    str
    parent_id: int | None = None  # 回复哪条评论（可选）


@router.get("/posts/{post_id}/comments")
def get_comments(post_id: int, openid: str | None = None):
    """评论列表，包含 parent_id 支持前端线程化渲染，附点赞数。"""
    try:
        comments = comment_list(post_id=post_id, status="approved")
        for c in comments:
            like_data = comment_like_counts(c["id"], openid)
            c["like_count"] = like_data["count"]
            c["liked"] = like_data["liked"]
        return ok({"items": comments, "total": len(comments)})
    except Exception as e:
        return err(str(e))


@router.post("/posts/{post_id}/comments")
def create_comment(post_id: int, body: CommentBody):
    """发评论，支持回复（parent_id）。"""
    try:
        post = post_get(post_id)
        if not post:
            return err("帖子不存在")
        user = user_get(body.openid)
        if not user:
            return err("请先设置昵称再评论")
        content = body.content.strip()
        if not content or len(content) > 500:
            return err("评论不能为空，且不超过 500 字")
        comment_id = comment_create(
            post_id         = post_id,
            content         = content,
            author_openid   = body.openid,
            author_nickname = user["nickname"],
            parent_id       = body.parent_id,
        )
        return ok({"comment_id": comment_id, "msg": "评论成功！"})
    except Exception as e:
        return err(str(e))


# ── 评论点赞 ─────────────────────────────────────

class CommentLikeBody(BaseModel):
    openid: str

@router.post("/comments/{comment_id}/like")
def like_comment(comment_id: int, body: CommentLikeBody):
    """评论点赞/取消点赞，切换操作"""
    try:
        result = comment_like(comment_id, body.openid)
        return ok(result)
    except Exception as e:
        return err(str(e))

@router.get("/comments/{comment_id}/like")
def get_comment_like(comment_id: int, openid: str | None = None):
    """获取评论点赞数据"""
    try:
        result = comment_like_counts(comment_id, openid)
        return ok(result)
    except Exception as e:
        return err(str(e))
