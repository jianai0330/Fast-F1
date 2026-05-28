"""
LLM 客户端：调用 DeepSeek API 生成分析报告
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

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


PROMPT_TEMPLATE = """你是一名 F1 专业数据分析师，请根据以下结构化数据生成一份专业且易读的中文分析报告。

【比赛信息】
赛事：{race_name}
环节：{session_type}
对比：{driver_a}（{team_a}）vs {driver_b}（{team_b}）
圈时：{driver_a} {lap_time_a} | {driver_b} {lap_time_b} | 差距 {gap}

【计算指标】
赛段时间差：
{sectors}

直线 & 油门效率：
{straights}

弯道攻略（部分关键弯角）：
{corners}

轮胎稳定性：
{tyre}

【输出格式】（严格按以下结构，使用 Markdown）
## 总体结论
（2~3句，点出核心差距，必须引用具体数字）

## 赛段分析
（结合 S1/S2/S3 时间差，分析各赛段优劣势，100~150字）

## 弯道攻略
（选取差异最显著的3~5个弯角展开分析，100~150字）

## 直线 & 油门效率
（最高速、油门使用率对比，分析原因，80~120字）

## 轮胎管理
（结合标准差和衰退斜率，评价稳定性，80~120字）

要求：专业术语需简短解释；普通 F1 观众可以读懂；结论必须有数据支撑。
"""


def generate_report(
    race_name: str,
    session_type: str,
    driver_a: str, team_a: str, lap_time_a: str,
    driver_b: str, team_b: str, lap_time_b: str,
    gap: str,
    metrics: dict
) -> str:
    """调用 DeepSeek 生成 Markdown 分析报告"""

    # 把指标转成精简文字，不传原始数组
    sectors_str = json.dumps(metrics.get("sectors", {}), ensure_ascii=False, indent=2)
    straights_str = json.dumps(metrics.get("straights", {}), ensure_ascii=False, indent=2)
    tyre_str = json.dumps(metrics.get("tyre", {}), ensure_ascii=False, indent=2)

    # 弯角只取差异显著的（最低速差 > 5km/h）
    corners = metrics.get("corners", [])
    key_corners = [
        c for c in corners
        if abs(float(c.get("min_speed_delta", "0 km/h").replace(" km/h", ""))) > 5
    ][:6]
    corners_str = json.dumps(key_corners, ensure_ascii=False, indent=2)

    prompt = PROMPT_TEMPLATE.format(
        race_name=race_name,
        session_type=session_type,
        driver_a=driver_a, team_a=team_a, lap_time_a=lap_time_a,
        driver_b=driver_b, team_b=team_b, lap_time_b=lap_time_b,
        gap=gap,
        sectors=sectors_str,
        straights=straights_str,
        corners=corners_str,
        tyre=tyre_str,
    )

    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500,
    )
    return response.choices[0].message.content
