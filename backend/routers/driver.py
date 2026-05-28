"""
车手评论接口

GET  /driver/{code}/comments        评论列表（?page=）
POST /driver/{code}/comments        发评论（需 openid + nickname）
POST /driver/comments/{id}/like     点赞
"""

import time
from fastapi import APIRouter
from pydantic import BaseModel
from models.response import ok, err
from db.database import (
    user_get,
    driver_comment_add, driver_comment_list, driver_comment_like,
)

router = APIRouter()

VALID_CODES = {
    "ANT","RUS","LEC","HAM","NOR","PIA","VER","TSU",
    "ALB","SAI","ALO","STR","GAS","DOO","HUL","BOR",
    "OCO","BEA","LAW","HAD","MAG",
}


class CommentBody(BaseModel):
    openid: str
    content: str


@router.get("/driver/{code}/comments")
def get_comments(code: str, page: int = 1):
    code = code.upper()
    if code not in VALID_CODES:
        return err("无效车手代码")
    items = driver_comment_list(code, page=page)
    # 格式化时间
    now = int(time.time())
    for item in items:
        diff = now - item["created_at"]
        if diff < 60:
            item["time_str"] = "刚刚"
        elif diff < 3600:
            item["time_str"] = f"{diff // 60}分钟前"
        elif diff < 86400:
            item["time_str"] = f"{diff // 3600}小时前"
        else:
            item["time_str"] = f"{diff // 86400}天前"
    return ok({"comments": items, "page": page})


@router.post("/driver/{code}/comments")
def post_comment(code: str, body: CommentBody):
    code = code.upper()
    if code not in VALID_CODES:
        return err("无效车手代码")
    content = body.content.strip()
    if not content:
        return err("评论不能为空")
    if len(content) > 200:
        return err("评论最多200字")

    user = user_get(body.openid)
    if not user:
        return err("请先在论坛注册昵称")
    nickname = user["nickname"]

    cid = driver_comment_add(code, content, body.openid, nickname)
    return ok({"id": cid, "nickname": nickname})


@router.post("/driver/comments/{comment_id}/like")
def like_comment(comment_id: int):
    likes = driver_comment_like(comment_id)
    return ok({"likes": likes})
