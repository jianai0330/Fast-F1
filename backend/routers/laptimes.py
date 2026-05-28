from fastapi import APIRouter
from models.response import ok, err
from services.fastf1_service import get_session, fmt_time, check_laps_available
import math

router = APIRouter()

def safe_str(val, default=''):
    """处理 NaN/NaT，返回字符串"""
    try:
        if val is None:
            return default
        s = str(val)
        if s in ('nan', 'NaT', 'None'):
            return default
        return s
    except Exception:
        return default

def safe_int(val, default=0):
    try:
        f = float(val)
        if math.isnan(f):
            return default
        return int(f)
    except Exception:
        return default

def safe_float(val, default=None):
    try:
        f = float(val)
        if math.isnan(f):
            return default
        return f
    except Exception:
        return default

@router.get("")
def get_laptimes(year: int = 2026, round_num: int = None, event: str = None, session: str = "R"):
    try:
        identifier = round_num if round_num else event
        s = get_session(year, identifier, session)

        # 检查 laps 数据是否可用
        laps_err = check_laps_available(s)
        if laps_err:
            return err(laps_err)

        drivers = s.laps['Driver'].unique().tolist()
        result = {}
        for drv in drivers:
            laps = s.laps.pick_drivers(drv).dropna(subset=['LapTime'])
            if len(laps) == 0:
                continue

            # 每圈数据
            laps_data = []
            for _, row in laps.iterrows():
                laps_data.append({
                    "lap":       int(row['LapNumber']),
                    "time":      fmt_time(row['LapTime']),
                    "time_s":    round(row['LapTime'].total_seconds(), 3),
                    "compound":  safe_str(row.get('Compound', '')),
                    "tyre_life": safe_int(row.get('TyreLife', 0)),
                    "pit_in":    safe_str(row.get('PitInTime', '')) not in ('', 'NaT'),
                    "pit_out":   safe_str(row.get('PitOutTime', '')) not in ('', 'NaT'),
                    "position":  safe_int(row.get('Position', 0)),
                })

            # 汇总数据
            times_s = [l["time_s"] for l in laps_data if l["time_s"] > 0]
            best_s = min(times_s) if times_s else None

            # 轮胎策略：按stint分组（pit_out=True开始新stint）
            stints = []
            cur_compound = None
            cur_count = 0
            for l in laps_data:
                cmp = l["compound"] or "UNKNOWN"
                if l["pit_out"] or cur_compound is None:
                    if cur_compound is not None:
                        stints.append({"compound": cur_compound, "laps": cur_count})
                    cur_compound = cmp
                    cur_count = 1
                else:
                    if cmp != cur_compound and cmp not in ("", "UNKNOWN"):
                        stints.append({"compound": cur_compound, "laps": cur_count})
                        cur_compound = cmp
                        cur_count = 1
                    else:
                        cur_count += 1
            if cur_compound is not None:
                stints.append({"compound": cur_compound, "laps": cur_count})

            # 进站次数 = pit_in 次数
            pit_count = sum(1 for l in laps_data if l["pit_in"])

            # 最终排名：取最后一圈的 position
            final_pos = laps_data[-1]["position"] if laps_data else 0

            result[drv] = {
                "team": laps['Team'].iloc[0] if len(laps) > 0 else "",
                "laps": laps_data,
                "summary": {
                    "final_position": final_pos,
                    "best_lap_s":     round(best_s, 3) if best_s else None,
                    "best_lap_fmt":   fmt_time_s(best_s) if best_s else "--",
                    "pit_count":      pit_count,
                    "total_laps":     len(laps_data),
                    "stints":         stints,
                }
            }
        return ok({"event": s.event["EventName"], "year": year, "session": session, "drivers": result})
    except Exception as e:
        return err(str(e))


def fmt_time_s(s):
    """把秒数格式化为 m:ss.mmm"""
    if s is None:
        return "--"
    m = int(s // 60)
    rem = s - m * 60
    return f"{m}:{rem:06.3f}"

