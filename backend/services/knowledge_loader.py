"""
F1知识库动态加载服务
根据赛道、session类型、分析场景等上下文，动态选择并组装知识片段注入LLM Prompt
"""
import json
import logging
import re
from pathlib import Path

# 知识库根目录
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
# Skills目录（项目根）
SKILLS_DIR = Path(__file__).parent.parent.parent / ".qoder" / "skills"

logger = logging.getLogger(__name__)

# ── 内部缓存 ──────────────────────────────────────────────
_tracks_cache: list | None = None
_tire_cache: dict | None = None
_strategy_cache: dict | None = None


def _load_tracks_json() -> list:
    """加载并缓存赛道特性数据"""
    global _tracks_cache
    if _tracks_cache is not None:
        return _tracks_cache
    filepath = KNOWLEDGE_DIR / "tracks" / "track_characteristics.json"
    try:
        _tracks_cache = json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[knowledge_loader] 赛道数据加载失败: {e}")
        _tracks_cache = []
    return _tracks_cache


def _load_tire_json() -> dict:
    """加载并缓存轮胎参考数据"""
    global _tire_cache
    if _tire_cache is not None:
        return _tire_cache
    filepath = KNOWLEDGE_DIR / "reference_data" / "tire_compounds_2026.json"
    try:
        _tire_cache = json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[knowledge_loader] 轮胎数据加载失败: {e}")
        _tire_cache = {}
    return _tire_cache


def _load_strategy_json() -> dict:
    """加载并缓存策略决策规则"""
    global _strategy_cache
    if _strategy_cache is not None:
        return _strategy_cache
    filepath = KNOWLEDGE_DIR / "decision_rules" / "strategy_rules.json"
    try:
        _strategy_cache = json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[knowledge_loader] 策略规则加载失败: {e}")
        _strategy_cache = {}
    return _strategy_cache


# ── 赛道匹配 ──────────────────────────────────────────────

def _get_track_info(race_name: str) -> dict | None:
    """从track_characteristics.json中匹配赛道

    匹配逻辑：race_name中包含track的name/country/official_name
    """
    tracks = _load_tracks_json()
    if not tracks:
        return None

    race_lower = race_name.lower()
    best_match = None
    best_score = 0

    for track in tracks:
        score = 0
        name = track.get("name", "").lower()
        country = track.get("country", "").lower()
        official = track.get("official_name", "").lower()

        if name and name in race_lower:
            score = 3  # 最精确匹配
        elif official and official in race_lower:
            score = 2
        elif country and country in race_lower:
            score = 1

        # 也尝试反向匹配：race_name的单词是否出现在track字段中
        if score == 0:
            for word in race_lower.split():
                if len(word) > 3 and (word in name or word in country or word in official):
                    score = 1
                    break

        if score > best_score:
            best_score = score
            best_match = track

    return best_match


# ── Skills内容提取 ──────────────────────────────────────────

def _extract_skill_sections(skill_file: str, section_numbers: list[str]) -> str:
    """从skill md文件中提取指定section的内容

    skill_file: 如 "f1-telemetry-analysis.md"
    section_numbers: 如 ["2", "4", "5"] 表示提取第2、4、5章节
    """
    filepath = SKILLS_DIR / skill_file
    if not filepath.exists():
        logger.debug(f"[knowledge_loader] Skill文件不存在: {filepath}")
        return ""

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"[knowledge_loader] Skill文件读取失败: {e}")
        return ""

    # 按 ## 数字. 标题 分割
    # 匹配如 "## 2. 关键指标解读规则" 或 "## 2.1 ..."
    pattern = re.compile(r'^(## \d+\..*)$', re.MULTILINE)
    sections = list(pattern.finditer(content))

    if not sections:
        # 降级：按 ## 标题分割（不含数字前缀）
        pattern2 = re.compile(r'^(## .*)$', re.MULTILINE)
        sections = list(pattern2.finditer(content))
        if not sections:
            return ""

    extracted = []
    for i, match in enumerate(sections):
        heading = match.group(1)
        # 提取章节号
        num_match = re.match(r'## (\d+)\.', heading)
        if num_match and num_match.group(1) in section_numbers:
            start = match.start()
            end = sections[i + 1].start() if i + 1 < len(sections) else len(content)
            section_text = content[start:end].strip()
            extracted.append(section_text)

    if not extracted:
        return ""

    return "\n\n".join(extracted)


# ── 各加载函数 ──────────────────────────────────────────────

def load_track_context(race_name: str) -> str:
    """根据赛事名加载对应赛道特性知识块

    race_name: 如 "Japanese Grand Prix" 或包含国家/城市名的字符串
    返回格式化的赛道知识文本（用于注入Prompt）
    """
    track = _get_track_info(race_name)
    if not track:
        return ""

    lines = [f"## 赛道：{track.get('name', '未知')}"]

    # 基本信息
    track_type = track.get("track_type", "unknown")
    tire_severity = track.get("tire_severity", "unknown")
    lines.append(f"- 类型：{track_type} | 轮胎退化等级：{tire_severity}")
    lines.append(f"- 均速：{track.get('avg_speed_kmh', '?')}km/h | "
                 f"弯角：{track.get('corners', '?')}个 | "
                 f"DRS区：{track.get('drs_zones', '?')}个")
    lines.append(f"- 进站损失：{track.get('typical_pit_loss_s', '?')}s | "
                 f"燃油修正：{track.get('fuel_correction_s_per_kg', '?')}s/kg")

    # 扇区特性
    sectors = track.get("sectors", {})
    if sectors:
        lines.append("- 扇区特性：")
        for sname, sinfo in sectors.items():
            lines.append(f"  {sname}({sinfo.get('type', '?')}): "
                         f"{sinfo.get('key_corners', '')} — "
                         f"{sinfo.get('notes', '')}")

    # 关键分析因素
    factors = track.get("key_analysis_factors", [])
    if factors:
        lines.append(f"- 关键分析因素：{'、'.join(factors)}")

    # 超车难度
    overtaking = track.get("overtaking_difficulty", "")
    if overtaking:
        lines.append(f"- 超车难度：{overtaking}")

    # 备注
    notes = track.get("notes", "")
    if notes:
        lines.append(f"- 备注：{notes}")

    return "\n".join(lines)


def load_analysis_methodology(session_type: str, track_type: str, tire_severity: str) -> str:
    """根据session类型和赛道特性，从Skills中加载对应的分析方法论片段

    - 排位赛 + 高速赛道 → 从 f1-telemetry-analysis.md 提取"关键指标解读"和"正确vs错误示例"
    - 排位赛 + 技术赛道 → 从 f1-sector-diagnosis.md 提取"根因诊断流程"
    - 正赛 → 从 f1-tire-strategy.md 提取"退化模型"和"策略判定"
    - 正赛 → 从 f1-race-narrative.md 提取"叙事原则"和"置信度规则"
    """
    is_race = "正赛" in session_type or "冲刺" in session_type or "Race" in session_type.lower()
    is_qualifying = "排位" in session_type or "Qualifying" in session_type.lower()

    blocks = []

    if is_qualifying:
        if track_type in ("power", "mixed"):
            # 高速/混合赛道：遥测分析方法论
            section = _extract_skill_sections("f1-telemetry-analysis.md", ["2", "4"])
            if section:
                blocks.append("### 遥测分析方法论\n" + _summarize(section, max_chars=400))
        if track_type in ("high_downforce", "mixed"):
            # 高下压力/混合赛道：扇区诊断流程
            section = _extract_skill_sections("f1-sector-diagnosis.md", ["3"])
            if section:
                blocks.append("### 扇区根因诊断\n" + _summarize(section, max_chars=400))
        # 所有排位赛：加载正确vs错误示例的精简版
        section = _extract_skill_sections("f1-telemetry-analysis.md", ["4"])
        if section:
            blocks.append("### 分析正反示例\n" + _summarize(section, max_chars=300))

    if is_race:
        # 正赛：轮胎退化模型
        section = _extract_skill_sections("f1-tire-strategy.md", ["1", "3"])
        if section:
            blocks.append("### 轮胎退化与策略\n" + _summarize(section, max_chars=400))

        # 正赛：叙事原则和置信度
        narrative_section = _extract_skill_sections("f1-race-narrative.md", ["1", "3"])
        if narrative_section:
            blocks.append("### 叙事与置信度\n" + _summarize(narrative_section, max_chars=300))

    if not blocks:
        # 默认：加载遥测分析的关键指标
        section = _extract_skill_sections("f1-telemetry-analysis.md", ["2"])
        if section:
            blocks.append("### 关键指标解读\n" + _summarize(section, max_chars=300))

    return "\n\n".join(blocks) if blocks else ""


def load_tire_reference(tire_severity: str) -> str:
    """当赛道轮胎退化等级为medium/high时，加载轮胎参考数据"""
    tire_data = _load_tire_json()
    if not tire_data:
        return ""

    compounds = tire_data.get("compounds", {})
    general = tire_data.get("general_rules", {})
    track_deg = tire_data.get("track_specific_degradation", {})
    reg_notes = tire_data.get("2026_regulation_notes", {})

    lines = ["### 轮胎参考数据(2026)"]

    # 基本参数
    for compound_name, info in compounds.items():
        cn = {"soft": "软胎", "medium": "中性胎", "hard": "硬胎"}.get(compound_name, compound_name)
        deg = info.get("degradation_rate_s_per_lap", "?")
        peak = info.get("peak_performance_laps", "?")
        temp = info.get("optimal_temp_range_c", "?")
        lines.append(f"- {cn}：退化{deg}s/圈 | 峰值{peak}圈 | 温度{temp}°C")

    # 通用规则
    if general:
        lines.append(f"- 软→中基准差：{general.get('soft_to_medium_delta_s', '?')}s")
        lines.append(f"- 脏气流升温：{general.get('dirty_air_temp_increase_c', '?')}°C")

    # 对应退化等级的赛道组说明
    if tire_severity == "high" and "high_degradation_tracks" in track_deg:
        lines.append(f"- 高退化赛道：{track_deg['high_degradation_tracks'].get('notes', '')}")
    elif tire_severity == "medium" and "medium_degradation_tracks" in track_deg:
        lines.append(f"- 中退化赛道：{track_deg['medium_degradation_tracks'].get('notes', '')}")

    # 2026规则变化
    if reg_notes:
        aero = reg_notes.get("active_aero_impact", "")
        pu = reg_notes.get("pu_deployment_changes", "")
        if aero:
            lines.append(f"- 2026空力：{aero}")
        if pu:
            lines.append(f"- 2026 PU：{pu}")

    return "\n".join(lines)


def load_strategy_rules(session_type: str) -> str:
    """正赛时加载策略决策规则"""
    strategy = _load_strategy_json()
    if not strategy:
        return ""

    lines = ["### 策略决策规则"]

    # Undercut规则
    undercut = strategy.get("undercut", {})
    if undercut:
        conditions = undercut.get("conditions", {})
        lines.append(f"- Undercut条件：轮胎优势≥{conditions.get('tire_delta_required_s_per_lap', '?')}s/圈，"
                      f"间距{conditions.get('minimum_gap_to_attempt_s', '?')}-{conditions.get('maximum_gap_to_benefit_s', '?')}s")
        lines.append(f"- 新胎前3圈优势：{conditions.get('fresh_tire_advantage_first_3_laps_s', '?')}/圈")

    # Overcut规则
    overcut = strategy.get("overcut", {})
    if overcut:
        best_tracks = overcut.get("best_tracks", [])
        conditions = overcut.get("conditions", {})
        lines.append(f"- Overcut适用：{', '.join(best_tracks[:4])}")
        lines.append(f"- 对手出站圈损失：{conditions.get('opponent_out_lap_time_loss_s', '?')}s")

    # 安全车策略
    sc = strategy.get("safety_car_pit_decision", {})
    if sc:
        lines.append("- 安全车进站：窗口已开→立即进站(净收益15-25s)；新胎<5圈→不进")

    # 赛道位置vs速度权衡
    position = strategy.get("track_position_vs_pace_tradeoff", {})
    if position:
        pos_tracks = position.get("position_priority_tracks", {})
        pace_tracks = position.get("pace_priority_tracks", {})
        if pos_tracks:
            lines.append(f"- 位置优先赛道：{', '.join(pos_tracks.get('tracks', [])[:4])}")
        if pace_tracks:
            lines.append(f"- 速度优先赛道：{', '.join(pace_tracks.get('tracks', [])[:4])}")

    return "\n".join(lines)


def load_gotchas() -> str:
    """加载常见分析错误提醒（始终加载，作为安全网）

    仅提取P0级别的最关键错误提醒（3-5条）
    """
    filepath = KNOWLEDGE_DIR / "gotchas" / "common_analysis_errors.md"
    if not filepath.exists():
        return ""

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"[knowledge_loader] Gotchas加载失败: {e}")
        return ""

    # P0级别的错误（从gotchas文件的优先级表中提取）
    # 根据文件内容，P0错误为：进站圈/出站圈、VSC/SC期间DRS无效
    p0_warnings = [
        "进站圈/出站圈数据必须排除——圈时暴增20-25s，会扭曲所有统计",
        "VSC/SC期间DRS无效——速度下降是规则限制而非性能问题",
        "燃油负载差异可解释5-8km/h直线速度差——stint末期轻油vs初期重油",
        "一停与两停的退化斜率不可直接对比——温度历史和燃油负载不同",
        "赛道演进(Evolution)：周五→周日圈时改善1.5-2.5s，跨session不可直接对比",
    ]

    lines = ["### 分析安全提醒(P0)"]
    for i, w in enumerate(p0_warnings, 1):
        lines.append(f"{i}. {w}")

    return "\n".join(lines)


# ── 辅助函数 ──────────────────────────────────────────────

def _summarize(text: str, max_chars: int = 400) -> str:
    """对长文本进行智能摘要式截断

    优先保留：标题行、表格行、关键结论行
    """
    if len(text) <= max_chars:
        return text

    lines = text.split("\n")
    kept = []
    char_count = 0

    for line in lines:
        # 保留标题行、表格行、列表行、关键结论
        is_important = (
            line.strip().startswith("#")
            or line.strip().startswith("|")
            or line.strip().startswith("-")
            or line.strip().startswith("❌")
            or line.strip().startswith("✅")
            or line.strip().startswith("**")
        )

        if is_important or char_count < max_chars * 0.7:
            kept.append(line)
            char_count += len(line) + 1
        else:
            # 非关键行，在预算内保留
            if char_count + len(line) + 1 <= max_chars:
                kept.append(line)
                char_count += len(line) + 1

        if char_count >= max_chars:
            break

    result = "\n".join(kept)
    if len(result) > max_chars:
        result = result[:max_chars - 3] + "..."
    return result


def _truncate_knowledge(full_block: str, max_chars: int = 2000) -> str:
    """截断知识块到指定字符数，优先保留前面的内容"""
    if len(full_block) <= max_chars:
        return full_block

    # 尝试在段落边界截断
    truncated = full_block[:max_chars]
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.7:
        truncated = truncated[:last_para]

    return truncated + "\n\n[知识块已截断]"


# ── 主入口 ──────────────────────────────────────────────

def build_knowledge_block(
    race_name: str,
    session_type: str,  # "排位赛" / "正赛" / "冲刺赛" 等
    metrics_summary: dict | None = None,  # metrics.summary 如果有的话
) -> str:
    """根据所有可用上下文，组装完整的知识块

    返回一个格式化字符串，直接注入到SYSTEM_PROMPT或USER_PROMPT中
    控制总长度不超过2000字（约500-600 tokens）
    """
    blocks = []

    try:
        # 1. 赛道特性（必选）
        track_ctx = load_track_context(race_name)
        if track_ctx:
            blocks.append(track_ctx)

        # 2. 从赛道知识中提取track_type和tire_severity
        track_info = _get_track_info(race_name)
        track_type = track_info.get("track_type", "mixed") if track_info else "mixed"
        tire_severity = track_info.get("tire_severity", "medium") if track_info else "medium"

        # 3. 分析方法论（根据session和赛道类型选择）
        methodology = load_analysis_methodology(session_type, track_type, tire_severity)
        if methodology:
            blocks.append(methodology)

        # 4. 轮胎参考（中/高退化赛道）
        if tire_severity in ("medium", "high"):
            tire_ref = load_tire_reference(tire_severity)
            if tire_ref:
                blocks.append(tire_ref)

        # 5. 策略规则（仅正赛/冲刺赛）
        if "正赛" in session_type or "冲刺" in session_type or "Race" in session_type.lower():
            strategy = load_strategy_rules(session_type)
            if strategy:
                blocks.append(strategy)

        # 6. Gotchas（始终加载精简版）
        gotchas = load_gotchas()
        if gotchas:
            blocks.append(gotchas)

    except Exception as e:
        logger.error(f"[knowledge_loader] 知识块构建异常: {e}")

    # 组装并控制长度
    full_block = "\n\n".join(blocks)
    return _truncate_knowledge(full_block, max_chars=2000)
