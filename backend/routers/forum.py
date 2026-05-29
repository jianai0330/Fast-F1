"""
论坛接口（用户 / 分区 / 帖子 / 评论）

POST /forum/users/register          注册或更新昵称
GET  /forum/users/me                获取用户信息

GET  /forum/sections                所有分区列表

GET  /forum/posts                   帖子列表（?section_id=&page=）
GET  /forum/posts/{id}              帖子详情
POST /forum/posts                   发帖

GET  /forum/posts/{id}/comments     评论列表
POST /forum/posts/{id}/comments     发评论
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
        # 开发模式：直接用 code 当 openid，方便本地测试
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
    """昵称校验：2-12字，不含特殊符号"""
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
    code:       str             # wx.login 返回的临时 code
    nickname:   str
    avatar_url: str = ""


class UpdateNicknameBody(BaseModel):
    openid:   str
    nickname: str


@router.post("/users/update-nickname")
def update_nickname(body: UpdateNicknameBody):
    """更新昵称（openid 不变）"""
    if not _valid_nickname(body.nickname):
        return err("昵称需 2-12 字，不含特殊符号")
    user = user_upsert(body.openid, body.nickname.strip(), "")
    return ok(user)


@router.post("/users/register")
def register_user(body: RegisterBody):
    """
    注册或更新昵称。
    前端传 wx.login code，后端换 openid（避免 AppSecret 外泄）。
    """
    if not _valid_nickname(body.nickname):
        return err("昵称需 2-12 字，不含特殊符号")

    openid = _code2openid(body.code)
    if not openid:
        return err("微信登录失败，请重试")

    user = user_upsert(openid, body.nickname.strip(), body.avatar_url)
    return ok(user)


@router.get("/users/me")
def get_user(openid: str):
    """获取用户信息"""
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
    openid:     str             # 已注册用户的 openid
    news_id:    int | None = None  # 关联新闻（可选）
    curated_id: int | None = None  # 关联精选内容（可选）


@router.get("/posts")
def get_posts(section_id: int | None = None, page: int = 1, page_size: int = 20,
              sort: str = "latest"):
    """帖子列表（只返回 approved），支持按分区过滤
    sort: "latest" 按时间倒序 | "hot" 按热度排序
    """
    if sort not in ("latest", "hot"):
        return err("sort 只支持 latest 或 hot")

    try:
        if sort == "hot":
            # 热度模式也必须尊重 section_id，避免分区页混入全站热门帖。
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
    """帖子详情，浏览数自动 +1"""
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
    """
    发帖。用户帖子 status=pending，等待审核后可见。
    AI 种子帖通过 post_create(is_seeded=True) 直接 approved。
    """
    try:
        # 校验用户存在
        user = user_get(body.openid)
        if not user:
            return err("请先设置昵称再发帖")

        # 内容校验
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
        return ok({
            "post_id": post_id,
            "msg": "发帖成功！"
        })
    except Exception as e:
        return err(str(e))


# ── 删帖 ────────────────────────────────────────

class DeletePostBody(BaseModel):
    openid: str

@router.delete("/posts/{post_id}")
def delete_post(post_id: int, body: DeletePostBody):
    """删除帖子，仅作者本人可删"""
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
    """点赞或点踩，再点同类型取消，切换类型直接替换"""
    if body.type not in ("like", "dislike"):
        return err("type 必须是 like 或 dislike")
    try:
        result = post_like(post_id, body.openid, body.type)
        return ok(result)
    except Exception as e:
        return err(str(e))

@router.get("/posts/{post_id}/like")
def get_like(post_id: int, openid: str | None = None):
    """获取帖子点赞数据"""
    try:
        result = post_like_counts(post_id, openid)
        return ok(result)
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════
# 评论接口
# ═══════════════════════════════════════════════

class CommentBody(BaseModel):
    content: str
    openid:  str


@router.get("/posts/{post_id}/comments")
def get_comments(post_id: int):
    """评论列表，只返回 approved，时间正序"""
    try:
        comments = comment_list(post_id=post_id, status="approved")
        return ok({"items": comments, "total": len(comments)})
    except Exception as e:
        return err(str(e))


@router.post("/posts/{post_id}/comments")
def create_comment(post_id: int, body: CommentBody):
    """
    发评论，status=pending，等待审核后可见。
    """
    try:
        # 校验帖子存在
        post = post_get(post_id)
        if not post:
            return err("帖子不存在")

        # 校验用户存在
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
        )
        return ok({
            "comment_id": comment_id,
            "msg": "评论成功！"
        })
    except Exception as e:
        return err(str(e))
