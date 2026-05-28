"""
LLM 客户端：调用 DeepSeek API 生成分析报告

Prompt 模板系统 v2：
- SYSTEM_PROMPT：分析师角色定义 + 方法论 + 归因维度 + 异常处理 + 置信度 + 知识基准 + 范例
- PROMPT_TEMPLATE：数据注入 + 输出格式指引（与规则引擎 metrics 字段对齐）
"""
import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
from .knowledge_loader import build_knowledge_block

logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
    return _client


# ---------------------------------------------------------------------------
# System Prompt：定义分析师角色、方法论、约束与范例
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一位资深F1技术分析师，面向中国F1车迷撰写专业对标分析报告。你必须严格遵循以下分析规范。

## 三层递进分析框架
1. 全圈速度结构：总差距分布在哪些扇区，哪个扇区是胜负手
2. 分段优势来源：每个扇区的时间差来自制动/弯心/出弯/直线哪个环节
3. 关键弯角机制：最大差异弯角的物理解读——必须归因到具体维度

## 势能因素归因维度
每个性能差异必须归因到以下维度之一或组合：
- 车辆设置：下压力级别/悬挂刚度/刹车平衡
- 驾驶风格：制动点选择/转向输入/油门控制细腻度
- 轮胎状态：温度窗口匹配/退化阶段/化合物特性差异
- 能量部署：MGU-K回收效率/部署策略/电池热管理
- 外部因素：天气变化/赛道橡胶演变/脏气流影响

## 异常数据处理原则
- 数据不完整或异常时：明确标注"数据受限"并说明原因
- 基于可用数据给出有限结论，标注置信度为"低"
- 严禁基于不完整数据过度推断因果关系
- 进站圈/出站圈/安全车圈数据已由规则引擎预处理排除

## 置信度标注规范
每个关键结论后必须标注置信度：
- [高置信度]：基于5圈以上稳定遥测数据+多参数交叉验证
- [中置信度]：基于3-5圈有限数据或单一参数来源
- [低置信度]：推测性结论，基于间接证据或不完整数据

## 专业知识基准
- 弯角分类：低速弯(<100km/h)、中速弯(100-180km/h)、高速弯(>180km/h)
- 轮胎退化基准：软胎0.08-0.15s/圈、中性胎0.04-0.08s/圈、硬胎0.02-0.05s/圈；高退化赛道(Bahrain/Barcelona/Lusail等)退化+50%
- 轮胎性能窗口：软胎3-8圈、中性胎5-15圈、硬胎8-25圈
- 策略判定：undercut需≥0.15s/圈轮胎优势+2.5-4.0s间距；overcut适合低退化赛道(Monaco/Imola/Monza等)
- 脏气流可导致跟车轮胎温度升高6-8°C
- 2026规则：主动空力降低弯中侧向载荷5-10%，电能占比提高影响出弯加速特性

## 输出风格范例
范例1（排位赛对标）：
## 一句话结论
Russell凭借S2高速弯群组的空力优势(+0.31s)和S3能量部署效率(+0.22s)以0.834s锁定杆位，Antonelli的底盘调教在中低速弯有竞争力但被高速区间吞噬。[高置信度]

## 关键时刻
1. Q3第一次尝试(Lap 4)：Russell在S1 esses段率先建立0.15s优势，源自入弯速度平均高4km/h(下压力设定更激进)
2. Q3第二次尝试(Lap 7)：Antonelli尝试延后制动追回时间，但T7入弯过热导致弯心速度反降2km/h，净损失0.08s
3. 最终圈对比：Russell的能量部署在S3直线实现满额输出，而Antonelli因S2过度消耗电池在直线段少部署约0.4MJ

## 速度对比
### 全圈结构
- S1: Russell +0.28s (高速弯群组下压力优势)
- S2: Russell +0.31s (T7-T9连续弯过载能力)
- S3: Russell +0.22s (能量部署效率+出弯牵引力)

### 分段优势来源
S2详解：差异集中在T7-T9三连弯
- T7入弯制动点：Russell晚3m制动(对前轴刚度信心更强)
- T8弯心速度：Russell高5km/h(空力平台更稳定)
- T9出弯加速：基本持平(后轮牵引力相当)

### 关键弯角机制
130R(最大差异弯角，Δ=0.12s)：
- Russell全油通过(241km/h弯心)，Antonelli微收油门(237km/h)
- 根因：Russell的底板下压力在高速区更稳定，允许更高弯心速度[高置信度]

## 轮胎与策略
- 软胎暖胎后第2圈即达最佳性能，两车热管理能力相当
- Antonelli的前胎温度偏高2°C(入弯激进驾驶风格导致)，可能轻微影响S2抓地力[中置信度]
- 正赛预判：Antonelli的轮胎管理风格可能在长stint中更有利

## 总评
Russell的优势来源明确：空力设定在高速弯群组的性能释放。这在铃鹿的S1 esses和130R得到充分体现。Antonelli需在低下压力赛道发挥低阻力设定优势。预期差距在功率赛道将缩小至0.3s以内。[中置信度]

范例2（正赛对标）：
## 一句话结论
Verstappen通过第28圈的关键undercut窗口(+0.6s净收益)和硬胎stint的稳定退化控制(0.03s/圈 vs Hamilton 0.06s/圈)赢得4.2s胜利。[高置信度]

## 关键时刻
1. Lap 28：Verstappen提前进站，软胎已退化至+0.08s/圈(接近cliff)，新中性胎crossover仅用1圈即追平[高置信度]
2. Lap 32：Hamilton跟进进站，但pit exit遇到慢车损失1.2s，undercut窗口关闭[高置信度]
3. Lap 45-52：Verstappen硬胎stint一致性极佳(std=0.12s)，而Hamilton硬胎退化加速(二次拟合显著)[中置信度]

## 速度对比
### 全圈结构
- S1: Verstappen +0.18s (直线尾速高3km/h，低阻力设定)
- S2: 基本持平 (+0.02s)
- S3: Verstappen +0.15s (出弯牵引力+能量部署)

### 分段优势来源
S1详解：直线优势来自低阻力设定，但T1入弯需更早制动(制动点提前2m)[中置信度]
S3详解：出弯加速阶段Verstappen的MGU-K部署更激进，直线前50m加速快0.3s[高置信度]

### 关键弯角机制
T1(低速重刹区，制动点差异最大)：
- Verstappen制动点更早但更稳定(入弯速度波动小)
- Hamilton更激进的制动风格增加前胎磨损，导致后期制动信心下降[中置信度]

## 轮胎与策略
- 燃油修正后Verstappen硬胎真实退化0.03s/圈，Hamilton 0.06s/圈——驾驶风格更保胎[高置信度]
- Hamilton的软胎cliff在第26圈检测到，比预期早2圈(赛道温度偏高导致)[中置信度]
- 一停策略在低退化赛道为最优选择，Verstappen的执行时间窗口精确[高置信度]

## 总评
Verstappen的胜利是策略执行+轮胎管理的双重胜利。undercut时机精准，硬胎stint退化控制出色。Hamilton在交通管理上吃亏，pit exit慢车成为转折点。[高置信度]"""


# ---------------------------------------------------------------------------
# User Prompt：数据注入 + 输出格式指引
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """⚠️ 重要：本数据来自 2026 赛季，请严格按照下方【车手身份】对应关系使用车手全名，禁止使用历史赛季信息推断车手身份。

【车手身份】
{driver_a} = {full_name_a}，所属车队：{team_a}
{driver_b} = {full_name_b}，所属车队：{team_b}

【比赛信息】
赛事：{race_name}
环节：{session_type}
对比：{full_name_a}（{driver_a}）vs {full_name_b}（{driver_b}）
圈时：{full_name_a} {lap_time_a} | {full_name_b} {lap_time_b} | 差距 {gap}

【分析概要】（来自 metrics.summary）
主导优势扇区：{dominant_sector}
主要胜负因素：{primary_factor}
数据置信度：{confidence}

【关键时刻（差距变化最大的圈）】（来自 metrics.key_laps，含多类型原因和detail描述）
{key_laps}

【赛段时间差】（A={full_name_a}, B={full_name_b}）
{sectors}

【关键弯道攻略】（A={full_name_a}, B={full_name_b}，动态筛选8-10个关键弯角）
{corners}

【直线 & 油门效率】（A={full_name_a}, B={full_name_b}）
{straights}

【轮胎稳定性】
{tyre}

【轮胎分段衰退】（含退化模型、cliff检测、燃油修正退化）
{stint_degradation}

【理想圈分析】（来自 metrics.ideal_lap，可选）
{ideal_lap}

【轮胎策略对比】（来自 metrics.tire_analysis，含策略对比、退化对比、一致性对比）
{tire_analysis}

【输出格式】（严格按以下结构，使用 Markdown）

## 一句话结论
（用一句话概括胜负手，必须引用关键数据和优势扇区，末尾标注置信度）

## 关键时刻
（从 key_laps 数据中挑出最重要的2-3个时刻，用叙事方式描述）
- reason=tire_cliff → 说明"轮胎性能断崖式下降"及对策略的紧急影响
- reason=pit_undercut_attempt → 解读"利用新胎窗口实施undercut"的时机与净收益
- reason=pit_overcut_defense → 解读"留在赛道执行overcut"的逻辑与风险
- reason=possible_drs_boost → 解读DRS对差距变化的影响
- reason=safety_car → 解读安全车对策略格局的重塑
- 每个时刻后标注置信度

## 速度对比
### 全圈结构
（先概述整体速度格局，指出哪个扇区是胜负手，引用 sectors 数据的 delta）

### 分段优势来源
（按胜负手扇区展开：时间差来自制动/弯心/出弯/直线哪个环节，
结合 corners 中的 brake_point_delta/min_speed_delta/exit_speed_delta 解读。
不要只罗列数据，要解释原因——"入弯速度高3km/h通常意味着更高的下压力设定"）

### 关键弯角机制
（选取1-2个最大差异弯角进行物理解读：速度差异的根因是什么？
必须归因到车辆设置/驾驶风格/轮胎状态/能量部署/外部因素，
参考 corner_type(low_speed/medium_speed/high_speed)辅助解读。
末尾标注置信度）

## 轮胎与策略
（结合 stint_degradation + tyre + tire_analysis 数据）
- 策略类型对比：谁一停谁两停，策略选择合理性
- 退化模型差异：线性vs加速退化(引用 degradation_model 和 r_squared)
- 轮胎悬崖：cliff_detected=true时，说明出现圈数和紧急程度
- 燃油修正退化：优先引用 fuel_corrected_degradation（真实轮胎退化）
- 理想圈潜力：ideal_lap可用时，说明 gap_to_ideal——谁还有更大提升空间
- 每个结论标注置信度

## 总评
（2-3句总结性判断，说明"为什么赢"而不只是"赢了什么"，末尾标注置信度）


要求：全程使用车手全名，不得使用三字码；专业术语需简短解释；普通F1观众可以读懂；每个观点必须有数据支撑，但数据服务于叙事。"""


def _replace_codes(text: str, d1: str, full1: str, d2: str, full2: str) -> str:
    """在 metrics JSON 字符串中把三字码替换为 '全名(三字码)' 格式"""
    text = text.replace(f'"{d1}"', f'"{full1}({d1})"')
    text = text.replace(f'"{d2}"', f'"{full2}({d2})"')
    return text


def generate_report(
    race_name: str,
    session_type: str,
    driver_a: str, team_a: str, lap_time_a: str,
    driver_b: str, team_b: str, lap_time_b: str,
    gap: str,
    metrics: dict,
    full_name_a: str = "",
    full_name_b: str = "",
) -> str:
    """调用 DeepSeek 生成 Markdown 分析报告"""
    # 全名兜底：没传就用三字码
    if not full_name_a:
        full_name_a = driver_a
    if not full_name_b:
        full_name_b = driver_b

    # 把指标转成精简文字，不传原始数组
    sectors_str = json.dumps(metrics.get("sectors", {}), ensure_ascii=False, indent=2)
    straights_str = json.dumps(metrics.get("straights", {}), ensure_ascii=False, indent=2)
    tyre_str = json.dumps(metrics.get("tyre", {}), ensure_ascii=False, indent=2)
    key_laps_str = json.dumps(metrics.get("key_laps", []), ensure_ascii=False, indent=2)
    stint_degradation_str = json.dumps(metrics.get("stint_degradation", {}), ensure_ascii=False, indent=2)

    # 使用规则引擎预筛选的关键弯角（动态阈值，8-10个）
    key_corners = metrics.get("key_corners", [])
    if not key_corners:
        # fallback: 如果预筛选为空，使用全量弯角
        key_corners = metrics.get("corners", [])
    corners_str = json.dumps(key_corners, ensure_ascii=False, indent=2)

    # 新增指标字符串化
    summary = metrics.get("summary", {})
    ideal_lap_str = json.dumps(metrics.get("ideal_lap", {}), ensure_ascii=False, indent=2)
    tire_analysis_str = json.dumps(metrics.get("tire_analysis", {}), ensure_ascii=False, indent=2)

    # metrics 里的三字码替换为全名，防止 LLM 误认
    sectors_str  = _replace_codes(sectors_str,  driver_a, full_name_a, driver_b, full_name_b)
    straights_str = _replace_codes(straights_str, driver_a, full_name_a, driver_b, full_name_b)
    tyre_str     = _replace_codes(tyre_str,     driver_a, full_name_a, driver_b, full_name_b)
    corners_str  = _replace_codes(corners_str,  driver_a, full_name_a, driver_b, full_name_b)
    key_laps_str = _replace_codes(key_laps_str, driver_a, full_name_a, driver_b, full_name_b)
    stint_degradation_str = _replace_codes(stint_degradation_str, driver_a, full_name_a, driver_b, full_name_b)
    ideal_lap_str = _replace_codes(ideal_lap_str, driver_a, full_name_a, driver_b, full_name_b)
    tire_analysis_str = _replace_codes(tire_analysis_str, driver_a, full_name_a, driver_b, full_name_b)

    user_prompt = PROMPT_TEMPLATE.format(
        race_name=race_name,
        session_type=session_type,
        driver_a=driver_a, team_a=team_a, lap_time_a=lap_time_a,
        driver_b=driver_b, team_b=team_b, lap_time_b=lap_time_b,
        full_name_a=full_name_a, full_name_b=full_name_b,
        gap=gap,
        dominant_sector=summary.get('dominant_sector', 'unknown'),
        primary_factor=summary.get('primary_factor', 'unknown'),
        confidence=summary.get('confidence', 'unknown'),
        key_laps=key_laps_str,
        sectors=sectors_str,
        straights=straights_str,
        corners=corners_str,
        tyre=tyre_str,
        stint_degradation=stint_degradation_str,
        ideal_lap=ideal_lap_str,
        tire_analysis=tire_analysis_str,
    )

    # 动态加载知识块
    knowledge_block = build_knowledge_block(
        race_name=race_name,
        session_type=session_type,
        metrics_summary=summary,
    )

    # 将知识块注入到system消息中（在SYSTEM_PROMPT之后追加）
    system_content = SYSTEM_PROMPT
    if knowledge_block:
        system_content += f"\n\n## 本场分析参考知识\n{knowledge_block}"
        logger.info(f"[llm_client] 知识块已注入，长度={len(knowledge_block)}字")

    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=3000,
    )
    return response.choices[0].message.content
