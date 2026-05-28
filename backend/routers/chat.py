"""
匿名聊天室接口（轻量 HTTP 轮询）

GET  /chat/messages?since_id=0    获取消息列表
POST /chat/send                   发送消息
GET  /chat/random-nickname        随机生成昵称
"""

import random
from fastapi import APIRouter, Query
from models.response import ok, err
from db.database import chat_get_messages, chat_send_message

router = APIRouter()

# 简单敏感词过滤
BLOCKED_WORDS = ["操", "草", "妈", "逼", "傻", "死"]


def _filter_content(text: str) -> str:
    for w in BLOCKED_WORDS:
        text = text.replace(w, "*")
    return text


@router.get("/messages")
async def get_messages(since_id: int = Query(0)):
    """获取 since_id 之后的消息，最多 50 条"""
    try:
        messages = chat_get_messages(since_id=since_id, limit=50)
        return ok(messages)
    except Exception as e:
        return err(str(e))


@router.post("/send")
async def send_message(body: dict):
    """发送消息"""
    try:
        nickname = body.get("nickname", "").strip()[:20] or "匿名车迷"
        content = body.get("content", "").strip()[:200]
        if not content:
            return err("消息不能为空")
        content = _filter_content(content)
        msg_id = chat_send_message(nickname, content)
        return ok({"id": msg_id})
    except Exception as e:
        return err(str(e))


@router.get("/random-nickname")
async def random_nickname():
    """随机生成一个匿名昵称"""
    prefixes = [
        "车迷", "围场观众", "赛道迷", "轮胎工程师",
        "策略师", "赛事总监", "遥测分析师", "空力专家"
    ]
    name = f"{random.choice(prefixes)}#{random.randint(1000, 9999)}"
    return ok({"nickname": name})
