import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from models.response import ok, err
import fastf1.ergast as ergast

router = APIRouter()

# 车队官方配色
TEAM_COLORS = {
    'Red Bull Racing': '#3671C6',
    'Ferrari': '#E8002D',
    'Mercedes': '#27F4D2',
    'McLaren': '#FF8000',
    'Aston Martin': '#229971',
    'Alpine': '#FF87BC',
    'Williams': '#64C4FF',
    'Racing Bulls': '#6692FF',
    'Kick Sauber': '#52E252',
    'Haas F1 Team': '#B6BABD',
}

DEFAULT_COLOR = '#888888'

# 内存缓存，TTL = 30 分钟
_cache: dict = {}
_CACHE_TTL = 7200  # 2小时，积分榜变化不频繁


def _cache_get(key):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None


def _cache_set(key, data):
    _cache[key] = (data, time.time())


def get_color(team_name: str) -> str:
    for k, v in TEAM_COLORS.items():
        if k.lower() in team_name.lower() or team_name.lower() in k.lower():
            return v
    return DEFAULT_COLOR


def _fetch_standings(year: int):
    """并行拉取三个 Ergast 接口"""
    e = ergast.Ergast()
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_driver = ex.submit(e.get_driver_standings, season=year)
        f_constr = ex.submit(e.get_constructor_standings, season=year)
        f_races  = ex.submit(e.get_race_results, season=year, result_type='driver')
        driver_raw  = f_driver.result()
        constr_raw  = f_constr.result()
        races_raw   = f_races.result()
    return driver_raw, constr_raw, races_raw


@router.get("")
def get_standings(year: int = 2026):
    cache_key = f"standings_{year}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return ok(cached)

    try:
        driver_raw, constr_raw, races_raw = _fetch_standings(year)

        # 车手积分榜
        driver_rows = []
        if driver_raw is not None and len(driver_raw.content) > 0:
            df = driver_raw.content[0]
            for _, row in df.iterrows():
                team = row['constructorNames'][0] if row.get('constructorNames') else ''
                driver_rows.append({
                    'position': int(row['position']),
                    'driver':   row['driverCode'] if row.get('driverCode') else row['familyName'][:3].upper(),
                    'name':     f"{row['givenName']} {row['familyName']}",
                    'team':     team,
                    'points':   float(row['points']),
                    'wins':     int(row['wins']),
                    'color':    get_color(team),
                })

        # 车队积分榜
        constructor_rows = []
        if constr_raw is not None and len(constr_raw.content) > 0:
            df = constr_raw.content[0]
            for _, row in df.iterrows():
                team = row['constructorName']
                constructor_rows.append({
                    'position': int(row['position']),
                    'team':     team,
                    'points':   float(row['points']),
                    'wins':     int(row['wins']),
                    'color':    get_color(team),
                })

        # 积分趋势：前5名车手，每轮累计积分
        driver_trend = []
        try:
            top5_codes = [r['driver'] for r in driver_rows[:5]]
            if races_raw is not None and len(races_raw.content) > 0:
                # 一次 pass 预计算每轮每车手积分，避免三层嵌套
                pts_by_code: dict[str, list[float]] = defaultdict(list)
                for df_round in races_raw.content:
                    code_pts = {
                        row.get('driverCode', ''): float(row.get('points', 0))
                        for _, row in df_round.iterrows()
                    }
                    for code in top5_codes:
                        pts_by_code[code].append(code_pts.get(code, 0.0))

                for code in top5_codes:
                    cum = 0.0
                    series = []
                    for rn, pts in enumerate(pts_by_code[code], 1):
                        cum += pts
                        series.append([rn, round(cum, 1)])
                    drv_info = next((r for r in driver_rows if r['driver'] == code), {})
                    driver_trend.append({
                        'code':   code,
                        'color':  drv_info.get('color', DEFAULT_COLOR),
                        'series': series,
                    })
        except Exception:
            pass  # trend 失败不影响主数据

        result = {
            'year':         year,
            'drivers':      driver_rows,
            'constructors': constructor_rows,
            'driver_trend': driver_trend,
        }
        _cache_set(cache_key, result)
        return ok(result)

    except Exception as e:
        return err(str(e))
