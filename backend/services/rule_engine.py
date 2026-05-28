"""
规则引擎：从遥测数据计算结构化分析指标
输出结果作为 LLM prompt 的输入
"""
import numpy as np
import pandas as pd
from scipy import stats


def analyze_corners(tel_a, tel_b, corner_distances: list, labels: list) -> list:
    """
    按弯角分段，计算每个弯角的刹车点、最低速、出弯速差异
    window: 弯角前100m ~ 弯角后150m
    """
    results = []
    for i, (dist, label) in enumerate(zip(corner_distances, labels)):
        win_start = dist - 100
        win_end   = dist + 150

        def get_window(tel):
            return tel[(tel['Distance'] >= win_start) & (tel['Distance'] <= win_end)]

        seg_a = get_window(tel_a)
        seg_b = get_window(tel_b)

        if seg_a.empty or seg_b.empty:
            continue

        # 刹车点（Brake=True 第一个点的距离）
        def brake_point(seg):
            braking = seg[seg['Brake'] == True]
            return braking['Distance'].min() if not braking.empty else None

        bp_a = brake_point(seg_a)
        bp_b = brake_point(seg_b)

        # 最低速（apex）
        min_spd_a = seg_a['Speed'].min()
        min_spd_b = seg_b['Speed'].min()

        # 出弯速（弯角后100m区间最高速）
        def exit_speed(tel):
            seg = tel[(tel['Distance'] >= dist) & (tel['Distance'] <= dist + 100)]
            return seg['Speed'].max() if not seg.empty else None

        exit_a = exit_speed(tel_a)
        exit_b = exit_speed(tel_b)

        result = {"corner": label}
        if bp_a is not None and bp_b is not None:
            delta_bp = bp_a - bp_b
            result["brake_point_delta"] = f"{delta_bp:+.0f}m"
            result["brake_point_note"] = "A brakes later" if delta_bp > 0 else "B brakes later"
        result["min_speed_a"] = round(float(min_spd_a), 1)
        result["min_speed_b"] = round(float(min_spd_b), 1)
        result["min_speed_delta"] = f"{min_spd_a - min_spd_b:+.1f} km/h"
        if exit_a and exit_b:
            result["exit_speed_delta"] = f"{exit_a - exit_b:+.1f} km/h"

        results.append(result)
    return results


def analyze_sectors(lap_a, lap_b, driver_a: str, driver_b: str) -> dict:
    """赛段时间差（S1/S2/S3）"""
    result = {}
    for s in ['Sector1Time', 'Sector2Time', 'Sector3Time']:
        try:
            t_a = lap_a[s]
            t_b = lap_b[s]
            if hasattr(t_a, 'iloc'):
                t_a = t_a.iloc[0]
            if hasattr(t_b, 'iloc'):
                t_b = t_b.iloc[0]
            if pd.isna(t_a) or pd.isna(t_b):
                continue
            delta = (t_a - t_b).total_seconds()
            faster = driver_a if delta < 0 else driver_b
            result[s.replace('Time', '')] = {
                "delta": f"{delta:+.3f}s",
                "faster": faster
            }
        except Exception:
            pass
    return result


def analyze_straights(tel_a, tel_b, driver_a: str, driver_b: str) -> dict:
    """直线效率：最高速、油门全开占比"""
    max_spd_a = tel_a['Speed'].max()
    max_spd_b = tel_b['Speed'].max()

    def throttle_pct(tel):
        full_open = (tel['Throttle'] > 98).sum()
        return round(full_open / len(tel) * 100, 1) if len(tel) > 0 else 0

    thr_a = throttle_pct(tel_a)
    thr_b = throttle_pct(tel_b)

    return {
        "top_speed_a": round(float(max_spd_a), 1),
        "top_speed_b": round(float(max_spd_b), 1),
        "top_speed_delta": f"{max_spd_a - max_spd_b:+.1f} km/h",
        "top_speed_faster": driver_a if max_spd_a > max_spd_b else driver_b,
        "throttle_pct_a": thr_a,
        "throttle_pct_b": thr_b,
        "throttle_pct_delta": f"{thr_a - thr_b:+.1f}%",
    }


def analyze_tyre_stability(laps_a, laps_b, driver_a: str, driver_b: str) -> dict:
    """轮胎稳定性：圈时标准差 + 衰退斜率"""

    def get_lap_times(laps):
        valid = laps.dropna(subset=['LapTime'])
        times = valid['LapTime'].apply(lambda t: t.total_seconds())
        return times.values

    def stability_stats(times):
        if len(times) < 3:
            return {"std": None, "slope": None}
        std = float(np.std(times))
        slope, _, _, _, _ = stats.linregress(np.arange(len(times)), times)
        return {"std": round(std, 3), "slope": round(float(slope), 4)}

    t_a = get_lap_times(laps_a)
    t_b = get_lap_times(laps_b)

    return {
        driver_a: stability_stats(t_a),
        driver_b: stability_stats(t_b),
        "note": "std=圈时标准差(s), slope=每圈衰退速率(s/lap)"
    }


def build_metrics(tel_a, tel_b, lap_a, lap_b, laps_a, laps_b,
                  driver_a: str, driver_b: str,
                  corner_distances: list, corner_labels: list) -> dict:
    """汇总所有维度指标"""
    return {
        "corners":   analyze_corners(tel_a, tel_b, corner_distances, corner_labels),
        "sectors":   analyze_sectors(lap_a, lap_b, driver_a, driver_b),
        "straights": analyze_straights(tel_a, tel_b, driver_a, driver_b),
        "tyre":      analyze_tyre_stability(laps_a, laps_b, driver_a, driver_b),
    }
