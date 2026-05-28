"""
车手评论接口

GET  /driver/{code}/comments        评论列表（?page=）
POST /driver/{code}/comments        发评论（需 openid + nickname）
POST /driver/comments/{id}/like     点赞
GET  /driver/{code}/rating          获取社区评分聚合 + 我的评分（?openid=）
POST /driver/{code}/rating          提交/更新评分
"""

import time
from fastapi import APIRouter
from pydantic import BaseModel
from models.response import ok, err
from db.database import (
    user_get,
    driver_comment_add, driver_comment_list, driver_comment_like,
    driver_rating_upsert, driver_rating_get_mine, driver_rating_aggregate,
)

router = APIRouter()

VALID_CODES = {
    "ANT","RUS","LEC","HAM","NOR","PIA","VER","TSU",
    "ALB","SAI","ALO","STR","GAS","COL","HUL","BOR",
    "OCO","BEA","LAW","HAD","LIN","BOT","PER",
}


class CommentBody(BaseModel):
    openid: str
    content: str


class RatingBody(BaseModel):
    openid: str
    speed: int
    consist: int
    defend: int
    wet: int
    mental: int


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


@router.get("/driver/{code}/rating")
def get_rating(code: str, openid: str = ""):
    code = code.upper()
    if code not in VALID_CODES:
        return err("无效车手代码")
    agg = driver_rating_aggregate(code)
    mine = driver_rating_get_mine(code, openid) if openid else None
    return ok({"aggregate": agg, "mine": mine})


@router.post("/driver/{code}/rating")
def post_rating(code: str, body: RatingBody):
    code = code.upper()
    if code not in VALID_CODES:
        return err("无效车手代码")
    for val in [body.speed, body.consist, body.defend, body.wet, body.mental]:
        if not (1 <= val <= 5):
            return err("评分必须在 1-5 之间")
    scores = {
        "speed": body.speed, "consist": body.consist,
        "defend": body.defend, "wet": body.wet, "mental": body.mental,
    }
    driver_rating_upsert(code, body.openid, scores)
    agg = driver_rating_aggregate(code)
    return ok({"aggregate": agg, "mine": scores})
