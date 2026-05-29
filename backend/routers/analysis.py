from fastapi import APIRouter
from models.response import ok, err
from services.fastf1_service import (
    get_session, fmt_time, get_corner_distances, get_corner_labels
)
from services.rule_engine import build_metrics
from services.llm_client import generate_report
from db.database import analysis_feedback_save, analysis_feedback_counts, analysis_feedback_user
import json, os, hashlib, time
import fastf1.ergast as ergast

router = APIRouter()

CACHE_DIR = os.path.join(os.path.dirname(__file__), "../cache/analysis")
os.makedirs(CACHE_DIR, exist_ok=True)


# ── 赛季上下文缓存（30分钟 TTL）──
_season_cache: dict = {}
_SEASON_TTL = 1800


def _get_season_context(year: int, d1: str, d2: str, session: str) -> str:
    """获取赛季上下文：积分榜位置、交锋记录(H2H)、赛季最佳完赛。"""
    cache_key = f"{year}_{d1}_{d2}_{session}"
    now = time.time()
    if cache_key in _season_cache and now - _season_cache[cache_key]["ts"] < _SEASON_TTL:
        return _season_cache[cache_key]["data"]
    try:
        e = ergast.Ergast()
        lines = []
        # 1. 积分榜位置
        standings_raw = e.get_driver_standings(season=year)
        pos_d1 = pos_d2 = pts_d1 = pts_d2 = None
        team_d1 = team_d2 = ""
        if standings_raw is not None and len(standings_raw.content) > 0:
            df_standings = standings_raw.content[-1]
            for _, row in df_standings.iterrows():
                code = row.get('driverCode', '')
                if code == d1:
                    pos_d1, pts_d1 = int(row['position']), float(row['points'])
                    team_d1 = row['constructorNames'][0] if row.get('constructorNames') else ''
                elif code == d2:
                    pos_d2, pts_d2 = int(row['position']), float(row['points'])
                    team_d2 = row['constructorNames'][0] if row.get('constructorNames') else ''
        if pos_d1 is not None and pos_d2 is not None:
            lines.append(f"当前积分榜：{d1}(P{pos_d1}, {int(pts_d1)}分, {team_d1}) vs {d2}(P{pos_d2}, {int(pts_d2)}分, {team_d2})")
        # 2. 交锋记录
        is_race = session.upper() == 'R'
        h2h_d1 = h2h_d2 = 0
        results_raw = e.get_race_results(season=year)
        if results_raw is not None and len(results_raw.content) > 0:
            for df_round in results_raw.content:
                if df_round is None or len(df_round) == 0:
                    continue
                try:
                    d1_rows = df_round[df_round['driverCode'] == d1]
                    d2_rows = df_round[df_round['driverCode'] == d2]
                    if not d1_rows.empty and not d2_rows.empty:
                        p1 = int(d1_rows.iloc[0]['position'])
                        p2 = int(d2_rows.iloc[0]['position'])
                        if p1 > 0 and p2 > 0:
                            if p1 < p2:
                                h2h_d1 += 1
                            else:
                                h2h_d2 += 1
                except (ValueError, TypeError, KeyError):
                    continue
        total_h2h = h2h_d1 + h2h_d2
        session_label = "正赛" if is_race else "排位赛"
        if total_h2h > 0:
            lines.append(f"{session_label}交锋记录(H2H)：{d1} {h2h_d1}-{h2h_d2} {d2}")
        # 3. 赛季最佳
        best_d1 = best_d2 = None
        if results_raw is not None:
            for df_round in results_raw.content:
                if df_round is None or len(df_round) == 0:
                    continue
                try:
                    d1_r = df_round[df_round['driverCode'] == d1]
                    d2_r = df_round[df_round['driverCode'] == d2]
                    if not d1_r.empty:
                        p = int(d1_r.iloc[0]['position'])
                        if p > 0 and (best_d1 is None or p < best_d1):
                            best_d1 = p
                    if not d2_r.empty:
                        p = int(d2_r.iloc[0]['position'])
                        if p > 0 and (best_d2 is None or p < best_d2):
                            best_d2 = p
                except (ValueError, TypeError, KeyError):
                    continue
        if best_d1 is not None and best_d2 is not None:
            lines.append(f"赛季最佳完赛：{d1}(P{best_d1}), {d2}(P{best_d2})")
        elif best_d1 is not None:
            lines.append(f"赛季最佳完赛：{d1}(P{best_d1})")
        elif best_d2 is not None:
            lines.append(f"赛季最佳完赛：{d2}(P{best_d2})")
        if not lines:
            return ""
        result = "赛季上下文：\n- " + "\n- ".join(lines)
        _season_cache[cache_key] = {"data": result, "ts": now}
        return result
    except Exception:
        return ""


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

        # 获取赛季上下文
        season_context = _get_season_context(year, d1, d2, session)

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
            season_context=season_context,
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


from pydantic import BaseModel

class FeedbackBody(BaseModel):
    cache_key: str
    analysis_type: str = "driver"
    openid: str
    rating: int
    comment: str = ""


@router.post("/feedback")
def submit_feedback(body: FeedbackBody):
    """提交分析反馈"""
    if body.rating not in (1, -1):
        return err("rating must be 1 or -1")
    result = analysis_feedback_save(
        cache_key=body.cache_key,
        analysis_type=body.analysis_type,
        openid=body.openid,
        rating=body.rating,
        comment=body.comment,
    )
    return ok(result)


@router.get("/feedback/{cache_key}")
def get_feedback(cache_key: str, openid: str = ""):
    """获取分析的反馈统计和当前用户反馈"""
    counts = analysis_feedback_counts(cache_key)
    user_fb = analysis_feedback_user(cache_key, openid) if openid else {"rating": 0, "comment": ""}
    return ok({**counts, **user_fb})
