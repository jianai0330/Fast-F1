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


def get_color(team_name: str) -> str:
    for k, v in TEAM_COLORS.items():
        if k.lower() in team_name.lower() or team_name.lower() in k.lower():
            return v
    return DEFAULT_COLOR


@router.get("")
def get_standings(year: int = 2026):
    try:
        e = ergast.Ergast()

        # 车手积分榜
        driver_standings_raw = e.get_driver_standings(season=year)
        driver_rows = []
        if driver_standings_raw is not None and len(driver_standings_raw.content) > 0:
            df = driver_standings_raw.content[0]
            for _, row in df.iterrows():
                driver_rows.append({
                    'position': int(row['position']),
                    'driver':   row['driverCode'] if row.get('driverCode') else row['familyName'][:3].upper(),
                    'name':     f"{row['givenName']} {row['familyName']}",
                    'team':     row['constructorNames'][0] if row.get('constructorNames') else '',
                    'points':   float(row['points']),
                    'wins':     int(row['wins']),
                    'color':    get_color(row['constructorNames'][0] if row.get('constructorNames') else ''),
                })

        # 车队积分榜
        constructor_standings_raw = e.get_constructor_standings(season=year)
        constructor_rows = []
        if constructor_standings_raw is not None and len(constructor_standings_raw.content) > 0:
            df = constructor_standings_raw.content[0]
            for _, row in df.iterrows():
                team = row['constructorName']
                constructor_rows.append({
                    'position': int(row['position']),
                    'team':     team,
                    'points':   float(row['points']),
                    'wins':     int(row['wins']),
                    'color':    get_color(team),
                })

        # 积分趋势：每轮次后的累计积分（前5名车手）
        driver_trend = []
        try:
            top5_codes = [r['driver'] for r in driver_rows[:5]]
            # 获取每轮次积分
            race_results = e.get_race_results(season=year, result_type='driver')
            if race_results is not None and len(race_results.content) > 0:
                # 按 round 聚合
                from collections import defaultdict
                cumulative = defaultdict(float)
                rounds = []
                seen_rounds = set()

                for i, df_round in enumerate(race_results.content):
                    round_num = i + 1
                    if round_num in seen_rounds:
                        continue
                    seen_rounds.add(round_num)
                    rounds.append(round_num)
                    for _, row in df_round.iterrows():
                        code = row.get('driverCode', '')
                        pts = float(row.get('points', 0))
                        cumulative[code] += pts

                for code in top5_codes:
                    # 重新按轮次计算累计
                    cum = 0.0
                    series = []
                    for i, df_round in enumerate(race_results.content):
                        rn = i + 1
                        pts_this_round = 0.0
                        for _, row in df_round.iterrows():
                            if row.get('driverCode', '') == code:
                                pts_this_round = float(row.get('points', 0))
                                break
                        cum += pts_this_round
                        series.append([rn, round(cum, 1)])

                    drv_info = next((r for r in driver_rows if r['driver'] == code), {})
                    driver_trend.append({
                        'code':   code,
                        'color':  drv_info.get('color', DEFAULT_COLOR),
                        'series': series,
                    })
        except Exception:
            pass  # trend 失败不影响主数据

        return ok({
            'year': year,
            'drivers': driver_rows,
            'constructors': constructor_rows,
            'driver_trend': driver_trend,
        })
    except Exception as e:
        return err(str(e))
