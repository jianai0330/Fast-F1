from fastapi import APIRouter
from models.response import ok, err
from services.fastf1_service import (
    get_session, fmt_time, get_corner_distances, get_corner_labels
)
from services.rule_engine import build_metrics
from services.llm_client import generate_report
import json, os, hashlib

router = APIRouter()

CACHE_DIR = os.path.join(os.path.dirname(__file__), "../cache/analysis")
os.makedirs(CACHE_DIR, exist_ok=True)


def cache_key(year, identifier, d1, d2, session) -> str:
    raw = f"{year}-{identifier}-{d1}-{d2}-{session}"
    return hashlib.md5(raw.encode()).hexdigest()


def load_cache(key: str):
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_cache(key: str, data: dict):
    path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@router.get("")
def get_analysis(
    year: int = 2026,
    round_num: int = None,
    event: str = None,
    d1: str = "ALB",
    d2: str = "ALO",
    session: str = "Q",
    force: bool = False,
):
    try:
        identifier = round_num if round_num else event
        ck = cache_key(year, identifier, d1, d2, session)
        if not force:
            cached = load_cache(ck)
            if cached:
                cached["cached"] = True
                return ok(cached)

        s = get_session(year, identifier, session)

        lap_a = s.laps.pick_drivers(d1).pick_fastest()
        lap_b = s.laps.pick_drivers(d2).pick_fastest()
        laps_a = s.laps.pick_drivers(d1)
        laps_b = s.laps.pick_drivers(d2)

        tel_a = lap_a.get_car_data().add_distance()
        tel_b = lap_b.get_car_data().add_distance()

        circuit_info = s.get_circuit_info()
        total_dist = max(tel_a['Distance'].max(), tel_b['Distance'].max())
        n_corners  = len(circuit_info.corners)
        corner_dist   = get_corner_distances(circuit_info, total_dist, n_corners)
        corner_labels = get_corner_labels(circuit_info)

        # 获取圈时信息
        lap_time_a = lap_a['LapTime']
        lap_time_b = lap_b['LapTime']
        if hasattr(lap_time_a, 'iloc'): lap_time_a = lap_time_a.iloc[0]
        if hasattr(lap_time_b, 'iloc'): lap_time_b = lap_time_b.iloc[0]

        delta_s = (lap_time_a - lap_time_b).total_seconds()
        faster  = d1 if delta_s < 0 else d2
        gap     = f"{abs(delta_s):.3f}s ({faster} faster)"

        team_a = str(lap_a['Team'].iloc[0]) if hasattr(lap_a['Team'], 'iloc') else str(lap_a['Team'])
        team_b = str(lap_b['Team'].iloc[0]) if hasattr(lap_b['Team'], 'iloc') else str(lap_b['Team'])

        # 从 session.results 取车手全名，防止 LLM 用三字码猜错人
        def get_full_name(results_df, code: str) -> str:
            row = results_df[results_df['Abbreviation'] == code]
            if not row.empty:
                return str(row.iloc[0]['FullName'])
            return code
        try:
            results_df = s.results
            full_name_a = get_full_name(results_df, d1)
            full_name_b = get_full_name(results_df, d2)
        except Exception:
            full_name_a, full_name_b = d1, d2

        # 规则引擎计算指标
        metrics = build_metrics(
            tel_a, tel_b, lap_a, lap_b, laps_a, laps_b,
            d1, d2, corner_dist, corner_labels
        )

        # LLM 生成报告
        session_name_map = {"Q": "排位赛", "R": "正赛", "S": "冲刺赛", "FP1": "练习赛1", "FP2": "练习赛2", "FP3": "练习赛3"}
        report = generate_report(
            race_name=s.event["EventName"],
            session_type=session_name_map.get(session, session),
            driver_a=d1, team_a=team_a, lap_time_a=fmt_time(lap_time_a),
            driver_b=d2, team_b=team_b, lap_time_b=fmt_time(lap_time_b),
            gap=gap,
            metrics=metrics,
            full_name_a=full_name_a,
            full_name_b=full_name_b,
        )

        result = {
            "metrics": metrics,
            "report": report,
            "cached": False,
            "track_name": s.event["EventName"],
        }
        save_cache(ck, result)
        return ok(result)

    except Exception as e:
        return err(str(e))
