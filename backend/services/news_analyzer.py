"""
新闻 AI 分析服务
输入：新闻 title + summary
输出：三段式解读（技术要点 / 通俗解释 / 赛况影响）
分析完成后自动同步为论坛种子帖子
"""

import logging
import re
from services.llm_client import get_client
from db.database import (
    news_get_unanalyzed, news_analysis_save,
    post_create, section_get_by_slug
)

logger = logging.getLogger(__name__)

# ── Prompt 模板 ─────────────────────────────────
NEWS_PROMPT = """你是 F1 技术分析专家，请对以下新闻进行三段式解读。

新闻标题：{title}
新闻摘要：{summary}

请严格按照以下格式输出，每段以对应 emoji 开头，段落之间用空行分隔：

🔬 技术要点
（用工程师视角解读，涉及规则/参数/原理，200字以内）

🏎️ 通俗解释
（用车迷能懂的比喻，让完全不懂机械的人也能理解，100字以内）

📊 赛况影响
（对本赛季或具体站点的实际影响分析，150字以内）

要求：专业术语需简短解释；必须紧扣新闻内容；不要编造未提及的信息。"""

# ── 分区归类关键词映射 ──────────────────────────
KEYWORD_MAP: list[tuple[str, list[str]]] = [
    # 赛站
    ("bahrain",       ["巴林", "bahrain", "sakhir", "萨基尔"]),
    ("saudi_arabia",  ["沙特", "saudi", "jeddah", "吉达"]),
    ("australia",     ["澳大利亚", "australia", "melbourne", "albert park", "墨尔本"]),
    ("japan",         ["日本", "japan", "suzuka", "铃鹿"]),
    ("china",         ["中国", "china", "shanghai", "上海"]),
    ("miami",         ["迈阿密", "miami"]),
    ("imola",         ["伊莫拉", "imola", "emilia"]),
    ("monaco",        ["摩纳哥", "monaco", "monte carlo"]),
    ("canada",        ["加拿大", "canada", "montreal", "蒙特利尔"]),
    ("spain",         ["西班牙", "spain", "barcelona", "巴塞罗那"]),
    ("austria",       ["奥地利", "austria", "red bull ring", "斯皮尔伯格"]),
    ("britain",       ["英国", "britain", "silverstone", "银石"]),
    ("belgium",       ["比利时", "belgium", "spa", "斯帕"]),
    ("hungary",       ["匈牙利", "hungary", "budapest", "布达佩斯"]),
    ("netherlands",   ["荷兰", "netherlands", "zandvoort", "赞德福特"]),
    ("italy",         ["意大利", "italy", "monza", "蒙扎"]),
    ("azerbaijan",    ["阿塞拜疆", "azerbaijan", "baku", "巴库"]),
    ("singapore",     ["新加坡", "singapore"]),
    ("usa",           ["美国", "usa", "austin", "cota", "奥斯汀"]),
    ("mexico",        ["墨西哥", "mexico"]),
    ("brazil",        ["巴西", "brazil", "sao paulo", "圣保罗", "interlagos"]),
    ("las_vegas",     ["拉斯维加斯", "las vegas"]),
    ("qatar",         ["卡塔尔", "qatar", "lusail", "路赛尔"]),
    ("abu_dhabi",     ["阿布扎比", "abu dhabi", "yas marina", "亚斯码头"]),
    # 车队
    ("redbull",       ["红牛", "red bull", "verstappen", "rb21", "lawson", "perez"]),
    ("ferrari",       ["法拉利", "ferrari", "sf-25", "leclerc", "hamilton", "sf25"]),
    ("mercedes",      ["梅赛德斯", "mercedes", "w16", "russell", "antonelli"]),
    ("mclaren",       ["迈凯伦", "mclaren", "norris", "piastri"]),
    ("aston_martin",  ["阿斯顿", "aston martin", "alonso", "stroll"]),
    ("alpine",        ["阿尔派因", "alpine", "gasly", "doohan"]),
    ("williams",      ["威廉姆斯", "williams", "albon", "sainz"]),
    ("racing_bulls",  ["racing bulls", "hadjar", "isack", "tsunoda"]),
    ("sauber",        ["索伯", "sauber", "bottas", "zhou", "hulkenberg"]),
    ("haas",          ["哈斯", "haas", "magnussen", "bearman", "occon"]),
    # general 兜底，放最后
    ("general",       []),
]

AI_BOT_OPENID   = "ai_bot"
AI_BOT_NICKNAME = "F1小助手 🤖"


def _classify_section(text: str) -> str:
    """根据文本关键词匹配分区 slug，默认返回 'general'"""
    text_lower = text.lower()
    for slug, keywords in KEYWORD_MAP:
        if not keywords:
            continue
        for kw in keywords:
            if kw.lower() in text_lower:
                return slug
    return "general"


def _parse_three_parts(raw: str) -> tuple[str, str, str]:
    """
    把 LLM 输出解析为三段：tech_points / plain_explain / race_impact
    按 emoji 标记分割，容错处理
    """
    tech   = plain = impact = ""

    # 尝试按 emoji 切割
    parts = re.split(r"(🔬|🏎️|📊)", raw)
    # parts 结构大概是 ['', '🔬', ' 技术...', '🏎️', ' 通俗...', '📊', ' 赛况...']
    current_key = None
    buf: dict[str, list[str]] = {"🔬": [], "🏎️": [], "📊": []}
    for p in parts:
        p = p.strip()
        if p in buf:
            current_key = p
        elif current_key and p:
            buf[current_key].append(p)

    tech   = "\n".join(buf["🔬"]).strip()
    plain  = "\n".join(buf["🏎️"]).strip()
    impact = "\n".join(buf["📊"]).strip()

    # 如果解析失败，整段放 tech_points
    if not tech and not plain and not impact:
        tech = raw.strip()

    return tech, plain, impact


def analyze_one(news_id: int, title: str, summary: str) -> bool:
    """
    对单条新闻进行 AI 分析，结果写入 news_analysis 表。
    成功返回 True，失败返回 False。
    """
    try:
        prompt = NEWS_PROMPT.format(title=title, summary=summary or title)
        client = get_client()
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content
        tech, plain, impact = _parse_three_parts(raw)

        news_analysis_save(news_id, tech, plain, impact, raw)
        logger.info(f"[news_analyzer] news_id={news_id} 分析完成")

        # 分析完成后同步到论坛种子帖
        _seed_to_forum(news_id, title, tech, plain, impact)
        return True

    except Exception as e:
        logger.error(f"[news_analyzer] news_id={news_id} 分析失败：{e}")
        return False


def _seed_to_forum(news_id: int, title: str,
                   tech: str, plain: str, impact: str):
    """把 AI 分析结果写入论坛作为种子帖（is_seeded=True，自动 approved）"""
    try:
        # 确定分区
        slug       = _classify_section(title)
        section    = section_get_by_slug(slug)
        section_id = section["id"] if section else section_get_by_slug("general")["id"]

        post_title   = f"[AI资讯] {title}"
        post_content = (
            f"🔬 **技术要点**\n{tech}\n\n"
            f"🏎️ **通俗解释**\n{plain}\n\n"
            f"📊 **赛况影响**\n{impact}"
        )

        post_create(
            section_id      = section_id,
            title           = post_title[:100],   # 截断保险
            content         = post_content,
            author_openid   = AI_BOT_OPENID,
            author_nickname = AI_BOT_NICKNAME,
            is_seeded       = True,
        )
        logger.info(f"[news_analyzer] 种子帖已写入 section={slug}")
    except Exception as e:
        logger.error(f"[news_analyzer] 种子帖写入失败：{e}")


def analyze_pending(limit: int = 5) -> dict:
    """
    批量分析尚未处理的新闻（供定时任务调用）。
    返回 {success, failed, total}
    """
    pending = news_get_unanalyzed(limit=limit)
    success = failed = 0
    for item in pending:
        ok = analyze_one(item["id"], item["title"], item.get("summary", ""))
        if ok:
            success += 1
        else:
            failed += 1
    return {"total": len(pending), "success": success, "failed": failed}
