"""
新闻 AI 分析服务
输入：新闻 title + summary
输出：递进式三段解读（事实摘要 / 深度解读 / 我们的判断）
分析完成后自动同步为论坛种子帖子
"""

import logging
import re
import time
import fastf1.ergast as ergast
from services.llm_client import get_client
from services.knowledge_loader import load_track_context
from db.database import (
    news_get_unanalyzed, news_analysis_save,
    post_create, section_get_by_slug
)

logger = logging.getLogger(__name__)

# ── RAG 上下文缓存（TTL 30分钟，避免每次分析都调 Ergast）──
_rag_cache: dict = {}
_RAG_TTL = 1800


def _needs_standings_context(title: str, summary: str) -> bool:
    """扩展语义匹配：捕获隐含的积分/格局影响"""
    text = f"{title} {summary}".lower()

    # 原有直接关键词
    direct_keywords = [
        "积分", "排名", "冠军", "standings", "points",
        "championship", "title", "领先", "差距",
        "赛季", "constructor", "世界冠军", "积分榜",
    ]

    # 隐含积分影响的关键词（间接影响格局的事件）
    indirect_keywords = [
        # 性能变化类
        "升级", "upgrade", "新部件", "性能提升", "速度提升",
        "PU", "引擎", "power unit", "空力套件",
        # 人员变动类
        "签约", "加盟", "离开", "退役", "换队",
        "技术总监", "首席", "工程师",
        # 处罚/规则类
        "罚退", "penalty", "违规", "禁赛", "预算帽",
        # 可靠性类
        "故障", "退赛", "DNF", "reliability", "可靠性",
        # 战略意义类
        "关键", "转折", "决定性", "夺冠", "争冠",
        "下半程", "收官",
    ]

    has_direct = any(kw in text for kw in direct_keywords)
    indirect_count = sum(1 for kw in indirect_keywords if kw in text)

    # 直接关键词命中，或间接关键词命中2个以上
    return has_direct or indirect_count >= 2


def _get_f1_context(title: str, content: str) -> str:
    """
    选择性注入积分榜：仅涉及积分/排名/冠军争夺时才拉取，30分钟缓存。
    不需要时返回空字符串，由调用方决定是否加入 prompt。
    """
    if not _needs_standings_context(title, content):
        return ""

    now = time.time()
    if "ctx" in _rag_cache and now - _rag_cache["ts"] < _RAG_TTL:
        return _rag_cache["ctx"]

    try:
        e = ergast.Ergast()
        driver_raw = e.get_driver_standings(season=2026)
        constr_raw = e.get_constructor_standings(season=2026)

        lines = ["=== 2026赛季积分数据（截至最新一站）==="]

        if driver_raw is not None and len(driver_raw.content) > 0:
            df = driver_raw.content[0].head(10)
            lines.append("车手积分榜（前10）：")
            for _, row in df.iterrows():
                team = row['constructorNames'][0] if row.get('constructorNames') else ''
                name = f"{row['givenName']} {row['familyName']}"
                lines.append(f"  P{int(row['position'])} {name} ({team}) {row['points']}分")

        if constr_raw is not None and len(constr_raw.content) > 0:
            df = constr_raw.content[0].head(5)
            lines.append("车队积分榜（前5）：")
            for _, row in df.iterrows():
                lines.append(f"  P{int(row['position'])} {row['constructorName']} {row['points']}分")

        ctx = "\n".join(lines)
        _rag_cache["ctx"] = ctx
        _rag_cache["ts"] = now
        return ctx

    except Exception as ex:
        logger.warning(f"[news_analyzer] RAG 上下文获取失败: {ex}")
        return ""


# ── 2026赛季强制上下文（不受RAG选择逻辑控制，始终注入）──
SEASON_2026_CONTEXT = """
## 2026赛季关键事实（强制参考）
- 当前时间：2026年5月
- 赛季进度：已完成约6-8站（具体以积分榜为准）
- 规则变化：50/50 ICE-MGU-K功率比、活跃空力、新轮胎规格
- 所有分析必须基于2026赛季事实，历史数据仅作对标参考

## 分析原则
- 赛况影响必须具体到车队/车手/赛道
- 每个结论需要因果链条支撑
- 不确定时标注置信度，不使用"可能影响"等空泛表述
"""

# ── 专业判断输出指令 ──────────────
JUDGMENT_INSTRUCTION = """
## 专业判断输出方法（第三段）

### 数据来源标注规则（极其重要）
每个具体数字必须标明来源，用户需要知道"这个数据哪来的"：
- [原文]：新闻中明确提到的数据，直接引用
- [推算]：基于原文数据的合理推导，需简述推导逻辑
- 若无法获得具体数字：用定性描述（如"显著提升"/"小幅改善"），绝不编造精确数字

### 禁止行为
❌ 凭空生成精确百分比（如"效率提升12%"——除非原文明确说了12%）
❌ 编造没有依据的圈时差异（如"+0.15s/圈"——除非有遥测数据支撑）
❌ 伪造积分变化预测（如"每站多拿5分"——除非基于明确的性能差距数据）
❌ 使用无来源的精确数字——任何数字必须标注[原文]或[推算]

### 正确做法
当原文提供数据时：
"Mercedes称MGU-K效率提升12%[原文]，按历史规律（每1%效率≈直线段+0.3km/h），预计直线速度提升约3-4km/h[推算]"

当原文未提供具体数据时：
"此次升级方向与2025年Red Bull的成功路径类似，预计将带来可观的直线速度提升，具体幅度需等FP1验证[待验证]"

### 判断结构四要素
1. 明确立场："我们认为..."（不是"可能..."）
2. 量化预测（有数据来源时标注[原文]/[推算]）或定性判断（无数据时，绝不编造数字）
3. 置信度：[高/中/低置信度]
4. 验证条件：何时何地可以验证这个判断

### 正确示例
💡 我们的判断
我们认为这次底板升级将提升Ferrari在中低速弯的表现。官方称下压力增加3%[原文]，按赛道模拟，这在匈牙利S2弯角群可转化为约0.1s的圈时收益[推算：基于3%下压力≈弯角速度+1.5km/h的经验公式]。Leclerc当前落后Verstappen 31分[积分榜数据]，若升级如预期生效，匈牙利+新加坡两站有望缩小8-12分差距[推算：基于历史同类升级的平均收益]。[中置信度]
验证条件：匈牙利FP2长跑中Ferrari的S2扇区时间是否优于巴塞罗那基线。

### 错误示例
❌ "升级将带来0.2秒/圈的提升"（没有来源，看起来像编的）
❌ "预计每站多拿6分"（凭空编造的数字）
❌ "效率提升15%"（文章没说15%，LLM自己编的）
❌ "这将影响Ferrari的竞争力，值得期待"（空泛无物）
❌ "将对2025赛季产生影响"（时间错误）
"""

# ── 深度解读方法论 ──────────────
DEPTH_ANALYSIS_RULES = """
## 深度解读方法论

所有类型新闻都必须给出深度解读（不再区分"技术类"和"非技术类"）：

### 数据来源标注要求
深度解读中引用的具体技术参数也必须标明来源：
- [原文]：新闻中明确提到的技术参数或数据
- [背景知识]：基于F1常识或历史数据的背景信息（如规则参数、赛道特性等）
- 若来源不确定，使用"据报道"、"一般认为"等限定词，不要当作确定事实

技术类新闻的解读角度：
- 工程原理：这个技术如何工作？物理机制是什么？
- 性能路径：技术→圈时→排位/正赛表现的传导链
- 引用技术参数时标注来源：如"新MGU-K输出350kW[原文]"、"2026规则限定电能占比50%[背景知识]"

人事类新闻的解读角度：
- 该人的技术/管理背景和擅长方向
- 对车队研发路线和组织效率的影响机制
- 历史案例类比（如Newey转会的先例效应）——标注[背景知识]

商业/规则类新闻的解读角度：
- 资源分配变化→研发优先级→赛道表现的传导
- 规则变化→车队适应能力差异→竞争格局重塑
- 引用规则细节时标注来源：如"预算帽1.35亿美元[背景知识]"
"""

# ── System 角色：所有分析的基础约束 ──────────────
NEWS_SYSTEM = f"""你是 F1 2026赛季专属数据分析师。当前时间是2026年，2026赛季正在进行中。

{SEASON_2026_CONTEXT}

{DEPTH_ANALYSIS_RULES}

{JUDGMENT_INSTRUCTION}

【时间认知 - 极其重要】
- 现在是2026年。2025赛季已于2025年11月底全部结束，它是历史。
- 你正在分析的新闻是2026赛季正在发生的当前事件。
- 绝对禁止出现"不会影响2025赛季"——2025赛季早已结束！
- 所有赛况影响分析必须聚焦在【2026赛季】，而非任何过去赛季。
- 错误示例（禁止）："此事件不会影响2025赛季的积分榜"
- 正确示例（必须）："此事件将影响2026赛季的积分格局"

【绝对禁止】
- 禁止提及 2025、2024 或更早赛季的任何积分、排名、成绩、冠军归属
- 禁止用"去年"、"上赛季"、"2025年"、"卫冕冠军(2025)"等表达方式
- 禁止根据历史规律推测当前赛季走势
- 若手头没有2026赛季的具体数据，必须明确写"2026赛季数据待更新"，严禁猜测

【当前赛季基本事实 - 2026赛季】
车手阵容：红牛(Verstappen/Lawson)、法拉利(Leclerc/Hamilton)、梅赛德斯(Russell/Antonelli)
迈凯伦(Norris/Piastri)、阿斯顿马丁(Alonso/Stroll)、阿尔派因(Gasly/Doohan)
威廉姆斯(Albon/Sainz)、RB(Hadjar/Tsunoda)、Audi(Hulkenberg/Bearman)、哈斯(Ocon/Magnussen)
动力单元规则：2026年全新混动规则，电能占比大幅提升至约50%

违反上述任何一条规则，分析将被视为无效。"""


# ── Prompt 模板 ─────────────────────────────────
NEWS_PROMPT = """{standings_block}{track_block}新闻标题：{title}
新闻正文：{content}

请按以下递进结构分析：

📋 事实摘要（80-120字）
客观提炼本条新闻的核心事实，不添加任何主观判断。回答"发生了什么"。

🔍 深度解读（100-200字）
分析事实背后的技术机制或产业逻辑。回答"为什么重要"和"通过什么机制产生影响"。
- 技术新闻：解析工程原理和性能影响路径
- 人事新闻：分析该人的技术/管理方向对车队研发的影响机制
- 商业新闻：分析资金/合作如何传导到赛道表现

💡 我们的判断（100-200字）
给出专业观点和可验证预测。必须包含：
1. 明确的立场/观点（不是"值得关注"，而是"我们认为X会导致Y"）
2. 预测：有数据支撑时给出量化预测（必须标注[原文]/[推算]来源）；无数据时用定性判断（如"显著提升"），绝不编造数字
3. 置信度标注：[高置信度]/[中置信度]/[低置信度]
4. 验证条件：在什么情况下可以验证这个预测

严禁：
- 第一段出现"可能"、"或许"等推测性词语
- 第三段使用"值得关注"、"有待观察"等空泛表述
- 任何对2025年及之前赛季的错误引用
"""

# ── 分区归类关键词映射 ──────────────────────────
KEYWORD_MAP: list[tuple[str, list[str]]] = [
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
    ("redbull",       ["红牛", "red bull", "verstappen", "rb21", "lawson"]),
    ("ferrari",       ["法拉利", "ferrari", "leclerc", "hamilton"]),
    ("mercedes",      ["梅赛德斯", "mercedes", "russell", "antonelli"]),
    ("mclaren",       ["迈凯伦", "mclaren", "norris", "piastri"]),
    ("aston_martin",  ["阿斯顿", "aston martin", "alonso", "stroll"]),
    ("alpine",        ["阿尔派因", "alpine", "gasly", "doohan"]),
    ("williams",      ["威廉姆斯", "williams", "albon", "sainz"]),
    ("racing_bulls",  ["racing bulls", "hadjar", "tsunoda"]),
    ("sauber",        ["audi", "奥迪", "hulkenberg", "bearman"]),
    ("haas",          ["哈斯", "haas", "ocon", "magnussen"]),
    ("general",       []),
]

AI_BOT_OPENID   = "ai_bot"
AI_BOT_NICKNAME = "F1小助手 🤖"


def _detect_track_context(title: str, content: str) -> str:
    """检测新闻是否涉及特定赛道，如果是则注入赛道上下文"""
    # 用于赛道匹配的关键词（仅包含赛道相关关键词，排除车队关键词）
    track_keywords = [
        ("bahrain", ["巴林", "bahrain", "sakhir", "萨基尔"]),
        ("saudi_arabia", ["沙特", "saudi", "jeddah", "吉达"]),
        ("australia", ["澳大利亚", "australia", "melbourne", "albert park", "墨尔本"]),
        ("japan", ["日本", "japan", "suzuka", "铃鹿"]),
        ("china", ["中国", "china", "shanghai", "上海"]),
        ("miami", ["迈阿密", "miami"]),
        ("imola", ["伊莫拉", "imola", "emilia"]),
        ("monaco", ["摩纳哥", "monaco", "monte carlo"]),
        ("canada", ["加拿大", "canada", "montreal", "蒙特利尔"]),
        ("spain", ["西班牙", "spain", "barcelona", "巴塞罗那"]),
        ("austria", ["奥地利", "austria", "red bull ring", "斯皮尔伯格"]),
        ("britain", ["英国", "britain", "silverstone", "银石"]),
        ("belgium", ["比利时", "belgium", "spa", "斯帕"]),
        ("hungary", ["匈牙利", "hungary", "budapest", "布达佩斯"]),
        ("netherlands", ["荷兰", "netherlands", "zandvoort", "赞德福特"]),
        ("italy", ["意大利", "italy", "monza", "蒙扎"]),
        ("azerbaijan", ["阿塞拜疆", "azerbaijan", "baku", "巴库"]),
        ("singapore", ["新加坡", "singapore"]),
        ("usa", ["美国", "usa", "austin", "cota", "奥斯汀"]),
        ("mexico", ["墨西哥", "mexico"]),
        ("brazil", ["巴西", "brazil", "sao paulo", "圣保罗", "interlagos"]),
        ("las_vegas", ["拉斯维加斯", "las vegas"]),
        ("qatar", ["卡塔尔", "qatar", "lusail", "路赛尔"]),
        ("abu_dhabi", ["阿布扎比", "abu dhabi", "yas marina", "亚斯码头"]),
    ]

    text_lower = (title + " " + content).lower()
    for track_name, keywords in track_keywords:
        for kw in keywords:
            if kw.lower() in text_lower:
                # 找到匹配的赛道，加载赛道知识
                context = load_track_context(kw)
                if context:
                    logger.info(f"[news_analyzer] 检测到赛道关键词'{kw}'，注入赛道知识")
                    return context
                break
    return ""


def _classify_section(text: str) -> str:
    text_lower = text.lower()
    for slug, keywords in KEYWORD_MAP:
        if not keywords:
            continue
        for kw in keywords:
            if kw.lower() in text_lower:
                return slug
    return "general"


def _parse_three_parts(raw: str) -> tuple[str, str, str]:
    """解析递进式三段输出：📋事实摘要 / 🔍深度解读 / 💡我们的判断"""
    tech = plain = impact = ""
    parts = re.split(r"(📋|🔍|💡)", raw)
    current_key = None
    buf: dict[str, list[str]] = {"📋": [], "🔍": [], "💡": []}
    for p in parts:
        p = p.strip()
        if p in buf:
            current_key = p
        elif current_key and p:
            buf[current_key].append(p)

    tech   = "\n".join(buf["📋"]).strip()   # 事实摘要 → tech_points
    plain  = "\n".join(buf["🔍"]).strip()   # 深度解读 → plain_explain
    impact = "\n".join(buf["💡"]).strip()   # 我们的判断 → race_impact

    if not tech and not plain and not impact:
        tech = raw.strip()

    return tech, plain, impact


def _smart_truncate(text: str, max_chars: int = 2000) -> str:
    """智能截断：优先保留开头和结尾（结论通常在首尾）"""
    if len(text) <= max_chars:
        return text

    # 分配：前60%给开头，后40%给结尾
    head_chars = int(max_chars * 0.6)
    tail_chars = max_chars - head_chars - 50  # 预留分隔符

    head = text[:head_chars]
    tail = text[-tail_chars:]

    return f"{head}\n\n[...中间内容省略...]\n\n{tail}"


def _fetch_full_text(url: str, fallback: str = "") -> str:
    """
    用 trafilatura 抓取文章正文，智能截取送给 AI。
    失败时降级返回 fallback（RSS 摘要）。
    """
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False,
                                       include_tables=False, no_fallback=False)
            if text and len(text.strip()) > 100:
                return _smart_truncate(text.strip())
    except Exception as e:
        logger.warning(f"[fetch_full_text] {url} 抓取失败: {e}")
    return fallback


def analyze_one(news_id: int, title: str, summary: str, url: str = "") -> bool:
    """对单条新闻进行 AI 分析，结果写入 news_analysis 表。
    优先抓取原文全文；若抓取失败则降级用 RSS 摘要。
    """
    try:
        # 抓全文，失败降级用摘要
        content = _fetch_full_text(url, fallback=summary or title) if url else (summary or title)

        # 选择性注入积分榜数据（RAG）
        f1_context = _get_f1_context(title, content)
        standings_block = f"【2026赛季积分参考】\n{f1_context}\n\n" if f1_context else ""

        # 检测新闻是否涉及特定赛道，如果是则注入赛道上下文
        track_context = _detect_track_context(title, content)
        track_block = f"【赛道特性参考】\n{track_context}\n\n" if track_context else ""

        prompt = NEWS_PROMPT.format(
            title=title,
            content=content,
            standings_block=standings_block,
            track_block=track_block,
        )

        # 构建system消息：强制注入赛季上下文（不受RAG选择逻辑控制）
        system_content = NEWS_SYSTEM

        client = get_client()
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=900,
        )
        raw = resp.choices[0].message.content
        tech, plain, impact = _parse_three_parts(raw)

        news_analysis_save(news_id, tech, plain, impact, raw)
        logger.info(f"[news_analyzer] news_id={news_id} 分析完成")

        _seed_to_forum(news_id, title, tech, plain, impact)
        return True

    except Exception as e:
        logger.error(f"[news_analyzer] news_id={news_id} 分析失败：{e}")
        return False


def _seed_to_forum(news_id: int, title: str,
                   tech: str, plain: str, impact: str):
    """把 AI 分析结果写入论坛作为种子帖"""
    try:
        slug       = _classify_section(title)
        section    = section_get_by_slug(slug)
        section_id = section["id"] if section else section_get_by_slug("general")["id"]

        post_title   = f"[AI资讯] {title}"
        post_content = (
            f"📋 **事实摘要**\n{tech}\n\n"
            f"🔍 **深度解读**\n{plain}\n\n"
            f"💡 **我们的判断**\n{impact}"
        )

        post_create(
            section_id      = section_id,
            title           = post_title[:100],
            content         = post_content,
            author_openid   = AI_BOT_OPENID,
            author_nickname = AI_BOT_NICKNAME,
            is_seeded       = True,
        )
        logger.info(f"[news_analyzer] 种子帖已写入 section={slug}")
    except Exception as e:
        logger.error(f"[news_analyzer] 种子帖写入失败：{e}")


def analyze_pending(limit: int = 5) -> dict:
    """批量分析尚未处理的新闻（供定时任务调用）。"""
    pending = news_get_unanalyzed(limit=limit)
    success = failed = 0
    for item in pending:
        result = analyze_one(item["id"], item["title"], item.get("summary", ""))
        if result:
            success += 1
        else:
            failed += 1
    return {"total": len(pending), "success": success, "failed": failed}


# ─────────────────────────────────────────────
# 精选内容 AI 分析（复用新闻分析的递进式三段逻辑）
# ─────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    """将 HTML 转为纯文本：去除标签，保留文本内容"""
    if not html:
        return ""
    # 去除 script/style 标签及内容
    text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text, flags=re.IGNORECASE)
    # 将 block 级标签转为换行
    for tag in ['br', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr']:
        text = re.sub(rf'<{tag}[^>]*>', '\n', text, flags=re.IGNORECASE)
    # 去除所有剩余 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 处理 HTML 实体
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#39;', "'").replace('&quot;', '"')
    # 清理多余空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def analyze_curated_content(curated_id: int, title: str,
                            content_html: str, url: str = "",
                            summary: str = "") -> bool:
    """
    分析精选内容，复用新闻分析的递进式三段逻辑。

    与新闻分析的区别：
    1. 内容来源是 content_html（已存储的HTML），不需要再抓取
    2. 需要先将HTML转为纯文本
    3. 如果 content_html 为空，尝试用 url 抓取
    4. summary 参数作为额外素材：当 HTML 和 URL 都拿不到内容时，用 summary
    5. 其他逻辑（RAG注入、知识加载、Prompt）完全复用
    """
    try:
        # 1. 将 content_html 转为纯文本
        content = _html_to_text(content_html)

        # 2. 如果 content_html 为空，尝试用 url 重新抓取
        if not content or len(content.strip()) < 50:
            if url:
                content = _fetch_full_text(url, fallback=title)
            # 如果 summary 有内容，用 title + summary 组合
            if (not content or len(content.strip()) < 50) and summary:
                content = f"{title}\n\n{summary}" if title != summary else summary
            elif not content:
                content = title
        else:
            # 智能截取，避免过长
            content = _smart_truncate(content)

        # 3. 选择性注入积分榜数据（RAG）
        f1_context = _get_f1_context(title, content)
        standings_block = f"【2026赛季积分参考】\n{f1_context}\n\n" if f1_context else ""

        # 4. 检测是否涉及特定赛道，注入赛道上下文
        track_context = _detect_track_context(title, content)
        track_block = f"【赛道特性参考】\n{track_context}\n\n" if track_context else ""

        # 5. 构建并调用 LLM（完全复用 NEWS_SYSTEM + NEWS_PROMPT）
        prompt = NEWS_PROMPT.format(
            title=title,
            content=content,
            standings_block=standings_block,
            track_block=track_block,
        )

        client = get_client()
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": NEWS_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=900,
        )
        raw = resp.choices[0].message.content
        tech, plain, impact = _parse_three_parts(raw)

        # 6. 保存到 curated_content 表的分析字段
        from db.database import curated_analysis_save
        curated_analysis_save(curated_id, tech, plain, impact)

        logger.info(f"[curated_analyzer] curated_id={curated_id} 分析完成")
        return True

    except Exception as e:
        logger.error(f"[curated_analyzer] curated_id={curated_id} 分析失败：{e}")
        return False
