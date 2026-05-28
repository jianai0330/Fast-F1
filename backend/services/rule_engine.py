"""
规则引擎：从遥测数据计算结构化分析指标
输出结果作为 LLM prompt 的输入

增强版：支持多类型关键时刻分类、动态弯角筛选、
轮胎悬崖检测、理想圈计算、燃油修正配速
"""
import statistics
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
        # 处理 corner_distances 为 NaN 的情况（2026赛季常见）
        if pd.isna(dist):
            continue

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

        # 推断弯角类型（基于最低速）
        min_speed_avg = (min_spd_a + min_spd_b) / 2
        if min_speed_avg < 100:
            corner_type = "low_speed"      # 慢速弯（发卡弯等）
        elif min_speed_avg < 180:
            corner_type = "medium_speed"    # 中速弯
        else:
            corner_type = "high_speed"      # 高速弯

        result = {"corner": label, "corner_type": corner_type}
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


# ---------------------------------------------------------------------------
# 关键时刻分类增强
# ---------------------------------------------------------------------------

def _classify_strategy(num_stints: int) -> str:
    """根据 stints 数量推断策略类型"""
    if num_stints <= 1:
        return "one_stop"
    elif num_stints == 2:
        return "two_stop"
    else:
        return "three_stop"


def _classify_moment_reason(moment_data: dict, va: pd.DataFrame,
                            vb: pd.DataFrame, gap_changes: list) -> list:
    """
    分类关键时刻原因为更细粒度的类型。

    可识别的类型：
    - pit_undercut_attempt: 车手A进站而B未进站，尝试undercut
    - pit_overcut_defense: 车手B进站而A未进站，A在执行overcut
    - simultaneous_pit: 两车同时进站
    - tire_cliff: 连续3圈退化加速，检测到轮胎悬崖
    - safety_car: 两车圈时同时飙升，疑似安全车/VSC
    - pace_difference: 默认配速差异
    """
    reasons = []

    lap_num = moment_data['lap']

    # --- 进站相关分类 ---
    a_pit = moment_data.get('pit_in_a', False) or moment_data.get('pit_out_a', False)
    b_pit = moment_data.get('pit_in_b', False) or moment_data.get('pit_out_b', False)

    if a_pit and not b_pit:
        reasons.append('pit_undercut_attempt')
    elif b_pit and not a_pit:
        reasons.append('pit_overcut_defense')
    elif a_pit and b_pit:
        reasons.append('simultaneous_pit')

    # --- 轮胎悬崖检测 ---
    # 检查该圈前后是否出现连续3圈圈时递增加速（退化斜率陡增）
    if not reasons or (len(reasons) == 1 and 'pit' not in str(reasons)):
        if _detect_tire_cliff_at_lap(lap_num, va, vb, gap_changes):
            reasons.append('tire_cliff')

    # --- 安全车/VSC检测 ---
    # 两车在同一圈的圈时同时远超中位数，说明可能出了安全车
    if not reasons:
        if _detect_safety_car_at_lap(lap_num, va, vb):
            reasons.append('safety_car')

    # --- DRS助推推断 ---
    # 如果某车突然单圈提速显著（gap_change绝对值大且无进站），可能是DRS助攻
    # 注意：此推断为粗略估计，精确判断需要遥测数据中的DRS信号
    if not reasons and abs(moment_data.get('gap_change', 0)) > 0.5:
        reasons.append('possible_drs_boost')

    # --- 默认：配速差异 ---
    if not reasons:
        reasons.append('pace_difference')

    return reasons


def _detect_tire_cliff_at_lap(lap_num: int, va: pd.DataFrame,
                               vb: pd.DataFrame, gap_changes: list) -> bool:
    """
    检测指定圈号附近是否出现轮胎悬崖（连续3圈退化加速）。
    判据：连续3圈的逐圈时间差递增（每圈比前一圈损失更多时间）。
    """
    def check_driver_clamp(valid_laps: pd.DataFrame, lap: int) -> bool:
        if lap not in valid_laps.index:
            return False
        # 取该圈前后各2圈（共5圈窗口）
        nearby_laps = sorted([l for l in valid_laps.index if lap - 2 <= l <= lap + 2])
        if len(nearby_laps) < 4:
            return False
        times = []
        for ln in nearby_laps:
            t = valid_laps.loc[ln, 'LapTime']
            if pd.isna(t):
                return False
            times.append(t.total_seconds())
        # 检查连续3圈的时间增量是否递增（二阶导数为正 → 退化加速）
        diffs = [times[i+1] - times[i] for i in range(len(times)-1)]
        consecutive_accel = 0
        for i in range(1, len(diffs)):
            if diffs[i] > diffs[i-1] > 0:  # 退化且在加速
                consecutive_accel += 1
                if consecutive_accel >= 2:  # 连续2次加速退化 = 至少3圈悬崖
                    return True
            else:
                consecutive_accel = 0
        return False

    # 只要有任一车手出现悬崖即返回True
    return check_driver_clamp(va, lap_num) or check_driver_clamp(vb, lap_num)


def _detect_safety_car_at_lap(lap_num: int, va: pd.DataFrame,
                               vb: pd.DataFrame) -> bool:
    """
    检测指定圈号是否可能为安全车圈。
    判据：两车该圈圈时都超过该选手中位数圈时的115%。
    """
    def is_slow_lap(valid_laps: pd.DataFrame, lap: int) -> bool:
        if lap not in valid_laps.index:
            return False
        t = valid_laps.loc[lap, 'LapTime']
        if pd.isna(t):
            return False
        all_times = valid_laps['LapTime'].dropna().apply(lambda x: x.total_seconds())
        if all_times.empty:
            return False
        median_time = all_times.median()
        return t.total_seconds() > median_time * 1.15

    return is_slow_lap(va, lap_num) and is_slow_lap(vb, lap_num)


def _determine_stint_phase(lap_num: int, total_laps: int) -> str:
    """根据圈号判断所处赛段阶段"""
    if total_laps <= 0:
        return 'unknown'
    ratio = lap_num / total_laps
    if ratio <= 0.25:
        return 'early'
    elif ratio <= 0.75:
        return 'mid'
    else:
        return 'late'


def identify_key_laps(laps_a, laps_b, driver_a: str, driver_b: str) -> list:
    """
    找出两车差距变化最大的圈，增强版支持多类型原因分类。

    返回: [{
        'lap': 28,
        'gap_change': 0.8,
        'reason': 'pit_stop',           # 向后兼容：主原因字符串
        'reasons': ['pit_undercut_attempt'],  # 增强版：细分类列表
        'detail': '车手A提前进站，利用新胎优势实施undercut',
        'driver_a_pit': True,
        'driver_b_pit': False,
        'stint_phase': 'mid'
    }, ...]
    """
    # 提取有效圈时
    def get_valid_laps(laps):
        valid = laps.dropna(subset=['LapTime']).sort_values('LapNumber')
        return valid[['LapNumber', 'LapTime', 'PitInTime', 'PitOutTime', 'Compound']].copy()

    va = get_valid_laps(laps_a)
    vb = get_valid_laps(laps_b)

    if va.empty or vb.empty:
        return []

    # 取两车都完成的圈号交集
    common_laps = set(va['LapNumber'].values) & set(vb['LapNumber'].values)
    if not common_laps:
        return []

    va = va[va['LapNumber'].isin(common_laps)].set_index('LapNumber')
    vb = vb[vb['LapNumber'].isin(common_laps)].set_index('LapNumber')

    # 计算每圈时间差 (A - B)，正值 = A 更慢 / B 拉开差距
    gap_changes = []
    prev_gap = None

    for lap_num in sorted(common_laps):
        if lap_num not in va.index or lap_num not in vb.index:
            continue
        t_a = va.loc[lap_num, 'LapTime']
        t_b = vb.loc[lap_num, 'LapTime']

        if pd.isna(t_a) or pd.isna(t_b):
            continue

        try:
            lap_gap = (t_a - t_b).total_seconds()
        except Exception:
            continue

        if prev_gap is not None:
            change = lap_gap - prev_gap  # 正值=A拉开差距，负值=B追回
            gap_changes.append({
                'lap': int(lap_num),
                'gap_change': round(change, 3),
                'pit_in_a': not pd.isna(va.loc[lap_num, 'PitInTime']),
                'pit_out_a': not pd.isna(va.loc[lap_num, 'PitOutTime']),
                'pit_in_b': not pd.isna(vb.loc[lap_num, 'PitInTime']),
                'pit_out_b': not pd.isna(vb.loc[lap_num, 'PitOutTime']),
            })

        prev_gap = lap_gap

    if not gap_changes:
        return []

    # 按绝对变化量排序，取 top 5（从3个扩展到5个）
    gap_changes.sort(key=lambda x: abs(x['gap_change']), reverse=True)
    top_n = gap_changes[:5]

    # 计算总圈数用于stint_phase判断
    total_laps = max(common_laps) if common_laps else 1

    # 分类原因并构建输出
    result = []
    for item in top_n:
        # 使用多类型分类
        classified_reasons = _classify_moment_reason(
            item, va, vb, gap_changes
        )

        # 向后兼容：主原因取第一个
        primary_reason = classified_reasons[0]

        # 判断进站状态
        driver_a_pit = item['pit_in_a'] or item['pit_out_a']
        driver_b_pit = item['pit_in_b'] or item['pit_out_b']

        # 生成人类可读的detail描述
        detail = _generate_moment_detail(
            item, classified_reasons, driver_a, driver_b
        )

        result.append({
            'lap': item['lap'],
            'gap_change': item['gap_change'],
            'reason': primary_reason,               # 向后兼容
            'reasons': classified_reasons,           # 增强版：完整原因列表
            'detail': detail,                        # 人类可读描述
            'driver_a_pit': driver_a_pit,
            'driver_b_pit': driver_b_pit,
            'stint_phase': _determine_stint_phase(item['lap'], total_laps),
        })

    # 按圈号排序输出
    result.sort(key=lambda x: x['lap'])
    return result


def _generate_moment_detail(item: dict, reasons: list,
                             driver_a: str, driver_b: str) -> str:
    """根据分类原因生成关键时刻的自然语言描述"""
    gap_change = item['gap_change']
    lap = item['lap']
    who_gains = driver_a if gap_change < 0 else driver_b
    gap_abs = abs(gap_change)

    if 'pit_undercut_attempt' in reasons:
        return (f"第{lap}圈，{driver_a}进站换胎尝试undercut，"
                f"净差距变化{gap_abs:.3f}s")
    elif 'pit_overcut_defense' in reasons:
        return (f"第{lap}圈，{driver_b}进站，{driver_a}留在赛道上执行overcut，"
                f"差距变化{gap_abs:.3f}s")
    elif 'simultaneous_pit' in reasons:
        return (f"第{lap}圈，两车同时进站，"
                f"差距变化{gap_abs:.3f}s")
    elif 'tire_cliff' in reasons:
        return (f"第{lap}圈附近检测到轮胎悬崖，圈时急剧上升，"
                f"{who_gains}受益{gap_abs:.3f}s")
    elif 'safety_car' in reasons:
        return (f"第{lap}圈疑似安全车/VSC，两车均减速，"
                f"差距变化{gap_abs:.3f}s")
    elif 'possible_drs_boost' in reasons:
        return (f"第{lap}圈{who_gains}可能获得DRS助攻，"
                f"单圈差距变化{gap_abs:.3f}s")
    else:
        return (f"第{lap}圈配速差异导致差距变化{gap_abs:.3f}s，"
                f"{who_gains}更快")


# ---------------------------------------------------------------------------
# 弯角筛选优化
# ---------------------------------------------------------------------------

def select_key_corners(corners: list, min_count: int = 8, max_count: int = 10) -> list:
    """
    动态阈值选择关键弯角，替代原来的固定5km/h阈值+仅保留6个。

    策略：
    1. 计算所有弯角的速度差异
    2. 动态阈值 = max(2, 中位数 * 0.3)，确保捕捉细微差异
    3. 结果限制在 min_count ~ max_count 之间
    4. 按差异绝对值排序保留最重要的弯角
    """
    if not corners:
        return []

    # 提取各弯角的速度差异绝对值
    deltas = []
    for c in corners:
        delta_str = c.get("min_speed_delta", "0 km/h")
        try:
            delta_val = abs(float(str(delta_str).replace(" km/h", "")))
        except (ValueError, TypeError):
            delta_val = 0.0
        deltas.append(delta_val)

    if not deltas:
        return corners[:min_count]

    # 动态阈值：取中位数的30%，最低2km/h
    median_delta = statistics.median(deltas) if deltas else 5
    threshold = max(2, median_delta * 0.3)

    # 按阈值筛选
    key_corners = [c for c, d in zip(corners, deltas) if d > threshold]

    # 保障数量在 min_count ~ max_count 之间
    if len(key_corners) > max_count:
        # 超过上限：按差异绝对值排序取前max_count个
        key_corners = sorted(
            key_corners,
            key=lambda c: abs(float(str(c.get("min_speed_delta", "0 km/h"))
                                    .replace(" km/h", ""))),
            reverse=True
        )[:max_count]
    elif len(key_corners) < min_count:
        # 不足下限：取差异最大的min_count个
        key_corners = sorted(
            corners,
            key=lambda c: abs(float(str(c.get("min_speed_delta", "0 km/h"))
                                    .replace(" km/h", ""))),
            reverse=True
        )[:min_count]

    return key_corners


# ---------------------------------------------------------------------------
# 轮胎退化模型升级
# ---------------------------------------------------------------------------

def _filter_valid_stint_laps(stint_laps: list, median_time: float) -> list:
    """
    过滤有效的 stint 圈次：
    - 排除前2圈（暖胎期，圈时不代表真实退化）
    - 排除异常圈（圈时 > 中位数 * 1.2，可能安全车等）
    """
    # 暖胎圈排除：跳过 stint 的前2圈
    warmup_count = 2
    filtered = stint_laps[warmup_count:] if len(stint_laps) > warmup_count + 2 else stint_laps

    # 排除异常高圈时
    if median_time > 0:
        filtered = [l for l in filtered if l['lap_time_s'] <= median_time * 1.2]

    return filtered


def _detect_tire_cliff(lap_times_s: list) -> dict:
    """
    检测轮胎悬崖：连续3圈退化速率加速。
    返回: {'detected': bool, 'cliff_start_index': int or None}
    """
    if len(lap_times_s) < 5:
        return {'detected': False, 'cliff_start_index': None}

    # 计算逐圈时间差（一阶差分）
    diffs = [lap_times_s[i+1] - lap_times_s[i] for i in range(len(lap_times_s) - 1)]

    # 检查差分是否连续递增（二阶差分为正 → 退化加速）
    for i in range(1, len(diffs) - 1):
        # 连续2次差分递增 = 至少3圈退化加速
        if diffs[i] > diffs[i-1] > 0 and diffs[i+1] > diffs[i] > 0:
            return {'detected': True, 'cliff_start_index': i}

    return {'detected': False, 'cliff_start_index': None}


def _compute_degradation(lap_numbers: np.ndarray, lap_times: np.ndarray,
                          min_samples: int = 4) -> dict:
    """
    计算退化斜率，优先使用二次拟合（检测加速退化），退化为线性拟合。
    至少需要 min_samples 个有效数据点（默认4，比原来的3更保守）。

    返回: {
        'model': 'quadratic' or 'linear',
        'degradation_slope': float,   # 主斜率（线性成分或二次项起始斜率）
        'quadratic_coeff': float,     # 二次项系数（仅quadratic模型）
        'r_squared': float,           # 拟合优度
    }
    """
    n = len(lap_numbers)
    if n < min_samples:
        return {
            'model': 'insufficient_data',
            'degradation_slope': 0.0,
            'quadratic_coeff': None,
            'r_squared': None,
        }

    # 标准化 x 避免数值不稳定
    x = lap_numbers - lap_numbers[0]
    y = lap_times

    # 先尝试二次拟合
    try:
        coeffs_quad = np.polyfit(x, y, 2)  # [a, b, c] → a*x² + b*x + c
        y_pred_quad = np.polyval(coeffs_quad, x)
        ss_res = np.sum((y - y_pred_quad) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_sq_quad = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 二次项系数显著（> 0.001 s/lap²）且拟合优度提升时使用二次模型
        quad_coeff = float(coeffs_quad[0])
        if abs(quad_coeff) > 0.001 and r_sq_quad > 0.3:
            # 主斜率取x中点处的切线斜率：2a*x_mid + b
            x_mid = float(np.median(x))
            slope_at_mid = 2 * quad_coeff * x_mid + float(coeffs_quad[1])
            return {
                'model': 'quadratic',
                'degradation_slope': round(float(slope_at_mid), 4),
                'quadratic_coeff': round(quad_coeff, 5),
                'r_squared': round(float(r_sq_quad), 3),
            }
    except Exception:
        pass

    # 退化为线性拟合
    try:
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        return {
            'model': 'linear',
            'degradation_slope': round(float(slope), 4),
            'quadratic_coeff': None,
            'r_squared': round(float(r_value ** 2), 3),
        }
    except Exception:
        return {
            'model': 'insufficient_data',
            'degradation_slope': 0.0,
            'quadratic_coeff': None,
            'r_squared': None,
        }


def analyze_stint_degradation(laps_a, laps_b, driver_a: str, driver_b: str) -> dict:
    """
    增强版轮胎分段衰退分析。

    新增功能：
    - 策略类型标注（one_stop/two_stop/three_stop）
    - stint位置标注（stint_1_of_2 等）
    - 暖胎圈排除（前2圈）
    - 二次拟合支持（检测加速退化）
    - 轮胎悬崖检测
    - 圈时一致性（标准差）
    - 燃油修正退化估算

    向后兼容：保留原有字段，增量添加新字段。
    """

    def compute_stints(laps, driver: str) -> list:
        valid = laps.dropna(subset=['LapTime']).sort_values('LapNumber').copy()
        if valid.empty:
            return []

        # 计算中位数圈时用于异常过滤
        times_s = valid['LapTime'].apply(lambda t: t.total_seconds())
        if times_s.empty:
            return []
        median_time = times_s.median()

        # 过滤 pit_in/pit_out 圈（进出站圈的圈时不可靠）
        valid = valid[
            valid['PitInTime'].isna() & valid['PitOutTime'].isna()
        ]

        # 赋值 LapTimeSeconds
        valid = valid.copy()
        valid['LapTimeSeconds'] = valid['LapTime'].apply(lambda t: t.total_seconds())

        # 按 Compound 变化点分段
        stints = []
        current_compound = None
        stint_laps = []

        for _, row in valid.iterrows():
            compound = row.get('Compound', None)
            if pd.isna(compound):
                compound = 'UNKNOWN'
            if compound != current_compound:
                if stint_laps and current_compound is not None:
                    stints.append({'compound': current_compound, 'laps': stint_laps})
                current_compound = compound
                stint_laps = []
            stint_laps.append({
                'lap_number': int(row['LapNumber']),
                'lap_time_s': float(row['LapTimeSeconds']),
            })

        if stint_laps and current_compound is not None:
            stints.append({'compound': current_compound, 'laps': stint_laps})

        # 标注策略类型和stint位置
        strategy_type = _classify_strategy(len(stints))

        # 计算每段退化
        result = []
        for idx, stint in enumerate(stints):
            n_total = len(stint['laps'])

            # 过滤有效圈次（排除暖胎圈和异常圈）
            filtered_laps = _filter_valid_stint_laps(stint['laps'], median_time)
            n_valid = len(filtered_laps)

            # 圈时列表（用于一致性计算和悬崖检测）
            all_lap_times_s = [l['lap_time_s'] for l in stint['laps']]
            filtered_times_s = [l['lap_time_s'] for l in filtered_laps]

            # 一致性：有效圈的标准差
            consistency_std = round(float(np.std(filtered_times_s)), 3) if n_valid >= 3 else None

            # 轮胎悬崖检测
            cliff_info = _detect_tire_cliff(all_lap_times_s)

            # 退化计算
            if n_valid >= 4:
                x = np.array([l['lap_number'] for l in filtered_laps], dtype=float)
                y = np.array([l['lap_time_s'] for l in filtered_laps], dtype=float)
                deg_result = _compute_degradation(x, y, min_samples=4)
            elif n_valid >= 1:
                # 数据不足4圈，退化不可靠
                deg_result = {
                    'model': 'insufficient_data',
                    'degradation_slope': 0.0,
                    'quadratic_coeff': None,
                    'r_squared': None,
                }
            else:
                deg_result = {
                    'model': 'no_data',
                    'degradation_slope': 0.0,
                    'quadratic_coeff': None,
                    'r_squared': None,
                }

            # 燃油修正退化：扣除燃油烧耗带来的圈时自然提升
            # 假设每圈烧1.5kg燃油，0.035s/kg的圈时影响
            fuel_corrected_slope = None
            if deg_result['degradation_slope'] != 0.0 and n_valid >= 4:
                # 燃油效应 ≈ 1.5 kg/lap * 0.035 s/kg = 0.0525 s/lap
                fuel_effect_per_lap = 1.5 * 0.035
                fuel_corrected_slope = round(
                    deg_result['degradation_slope'] - fuel_effect_per_lap, 4
                )

            stint_entry = {
                # 向后兼容字段
                'compound': stint['compound'],
                'laps': n_total,
                'degradation_slope': deg_result['degradation_slope'],
                # 增强字段
                'strategy_type': strategy_type,
                'stint_position': f"stint_{idx+1}_of_{len(stints)}",
                'degradation_model': deg_result['model'],
                'consistency_std': consistency_std,
                'cliff_detected': cliff_info['detected'],
                'cliff_lap': (
                    stint['laps'][cliff_info['cliff_start_index']]['lap_number']
                    if cliff_info['detected'] and cliff_info['cliff_start_index'] is not None
                    and cliff_info['cliff_start_index'] < len(stint['laps'])
                    else None
                ),
                'fuel_corrected_degradation': fuel_corrected_slope,
            }

            # 可选字段：仅在有意义时添加
            if deg_result.get('quadratic_coeff') is not None:
                stint_entry['quadratic_coeff'] = deg_result['quadratic_coeff']
            if deg_result.get('r_squared') is not None:
                stint_entry['r_squared'] = deg_result['r_squared']

            result.append(stint_entry)

        return result

    result_a = compute_stints(laps_a, driver_a)
    result_b = compute_stints(laps_b, driver_b)

    # 构建策略对比描述
    strategy_a = result_a[0]['strategy_type'] if result_a else 'unknown'
    strategy_b = result_b[0]['strategy_type'] if result_b else 'unknown'

    return {
        driver_a: result_a,
        driver_b: result_b,
        'note': 'degradation_slope=每圈圈时增加秒数(s/lap)，正值=衰退，越大越严重；'
                'fuel_corrected_degradation=扣除燃油效应后的真实轮胎退化；'
                'cliff_detected=是否检测到轮胎悬崖',
        'strategy_comparison': f"{strategy_a} vs {strategy_b}",
    }


# ---------------------------------------------------------------------------
# 新增指标：理想圈计算
# ---------------------------------------------------------------------------

def calculate_ideal_lap(laps_a, laps_b, driver_a: str, driver_b: str) -> dict:
    """
    计算理想圈：各扇区最佳时间的组合。
    理想圈与实际最快圈的差距反映了车手在不同扇区的潜力空间。
    """
    def compute_ideal(laps):
        valid = laps.dropna(subset=['LapTime']).copy()
        if valid.empty:
            return None

        best_sectors = {}
        for s_field, s_name in [('Sector1Time', 'S1'), ('Sector2Time', 'S2'), ('Sector3Time', 'S3')]:
            try:
                sector_times = valid[s_field].dropna()
                if sector_times.empty:
                    continue
                # 确保取标量值
                best = sector_times.min()
                if hasattr(best, 'total_seconds'):
                    best_sectors[s_name] = best.total_seconds()
                else:
                    best_sectors[s_name] = float(best)
            except Exception:
                continue

        if len(best_sectors) < 3:
            return None  # 扇区数据不完整，无法计算理想圈

        ideal_time = sum(best_sectors.values())

        # 实际最快圈
        fastest_lap = valid['LapTime'].min()
        if hasattr(fastest_lap, 'total_seconds'):
            actual_best = fastest_lap.total_seconds()
        else:
            actual_best = float(fastest_lap)

        return {
            'ideal_lap': round(ideal_time, 3),
            'actual_best': round(actual_best, 3),
            'gap_to_ideal': round(actual_best - ideal_time, 3),
            'best_sectors': {k: round(v, 3) for k, v in best_sectors.items()},
        }

    ideal_a = compute_ideal(laps_a)
    ideal_b = compute_ideal(laps_b)

    result = {'note': 'ideal_lap=各扇区最佳时间之和，gap_to_ideal=实际最快圈与理想圈的差距'}
    if ideal_a is not None:
        result[driver_a] = ideal_a
    if ideal_b is not None:
        result[driver_b] = ideal_b

    return result


# ---------------------------------------------------------------------------
# 新增指标：燃油修正配速
# ---------------------------------------------------------------------------

def calculate_fuel_corrected_pace(laps, fuel_start_kg: float = 100,
                                   fuel_per_lap_kg: float = 1.5) -> dict:
    """
    燃油修正后的真实配速。
    随着比赛进行，燃油烧耗减轻车重，圈时自然会提升。
    扣除这个效应后可以看到"纯配速"（排除轮胎退化和燃油效应后的能力）。

    参数：
    - fuel_start_kg: 赛车起始燃油量（kg），默认100kg
    - fuel_per_lap_kg: 每圈燃油消耗（kg），默认1.5kg/lap
    - 修正因子: 0.035 s/kg（每减少1kg车重，圈时减少约0.035秒）

    返回: {
        'corrected_laps': [{'lap': 1, 'raw_time': 92.5, 'corrected_time': 92.5, 'fuel_effect': 0.0}],
        'fuel_effect_total': 3.15,  # 全程燃油效应总计
        'avg_corrected_pace': 91.8,  # 燃油修正后平均圈时
    }
    """
    valid = laps.dropna(subset=['LapTime']).sort_values('LapNumber').copy()
    if valid.empty:
        return {'corrected_laps': [], 'fuel_effect_total': 0, 'avg_corrected_pace': None}

    correction_factor = 0.035  # s/kg，经验值

    corrected_laps = []
    for i, (_, row) in enumerate(valid.iterrows()):
        lap_time = row['LapTime']
        if hasattr(lap_time, 'total_seconds'):
            raw_time = lap_time.total_seconds()
        else:
            raw_time = float(lap_time)

        # 当前圈剩余燃油
        fuel_remaining = fuel_start_kg - (i * fuel_per_lap_kg)
        fuel_remaining = max(0, fuel_remaining)  # 不能为负

        # 燃油效应：从起始到当前圈，燃油减轻带来的圈时提升
        fuel_burned = fuel_start_kg - fuel_remaining
        fuel_effect = fuel_burned * correction_factor

        # 修正后圈时 = 原始圈时 - 燃油效应（把燃油减轻的"免费提速"扣除）
        corrected_time = raw_time - fuel_effect

        corrected_laps.append({
            'lap': int(row['LapNumber']),
            'raw_time': round(raw_time, 3),
            'corrected_time': round(corrected_time, 3),
            'fuel_effect': round(fuel_effect, 3),
        })

    # 汇总统计
    total_fuel_effect = corrected_laps[-1]['fuel_effect'] if corrected_laps else 0
    corrected_times = [cl['corrected_time'] for cl in corrected_laps]
    avg_corrected = round(statistics.mean(corrected_times), 3) if corrected_times else None

    return {
        'corrected_laps': corrected_laps[:5] + corrected_laps[-5:],  # 只保留前5+后5避免数据过多
        'fuel_effect_total': round(total_fuel_effect, 3),
        'avg_corrected_pace': avg_corrected,
        'note': 'corrected_time=扣除燃油减轻效应后的圈时，'
                'fuel_effect=从发车到当前圈的累计燃油修正量',
    }


# ---------------------------------------------------------------------------
# 增强版汇总函数
# ---------------------------------------------------------------------------

def _determine_dominant_sector(sectors: dict) -> str:
    """判断哪个扇区差距最大"""
    max_delta = 0
    dominant = None
    for sector_name, sector_data in sectors.items():
        try:
            delta = abs(float(str(sector_data.get('delta', '0s')).replace('s', '')))
            if delta > max_delta:
                max_delta = delta
                dominant = sector_name
        except (ValueError, TypeError):
            continue
    return dominant or 'unknown'


def _determine_primary_factor(corners: list, straights: dict,
                               sectors: dict, tyre: dict) -> str:
    """
    推断主导胜负因素。
    基于各维度指标差异的相对大小来判断。
    """
    factors = {}

    # 高速弯优势（弯角最低速差 > 3km/h 的弯角数量占比）
    if corners:
        high_speed_corner_advantage = sum(
            1 for c in corners
            if abs(float(str(c.get('min_speed_delta', '0 km/h')).replace(' km/h', ''))) > 3
        )
        factors['high_speed_corner_confidence'] = high_speed_corner_advantage

    # 直线速度优势
    try:
        top_speed_delta = abs(float(str(straights.get('top_speed_delta', '0 km/h')).replace(' km/h', '')))
        factors['straight_line_speed'] = top_speed_delta
    except (ValueError, TypeError):
        pass

    # 轮胎管理优势
    for driver_key, driver_data in tyre.items():
        if isinstance(driver_data, dict) and driver_data.get('slope') is not None:
            factors[f'tire_management_{driver_key}'] = abs(driver_data['slope'])

    # 返回最大的因素
    if not factors:
        return 'overall_pace'

    primary = max(factors, key=factors.get)
    return primary


def _determine_confidence(corners: list, sectors: dict, key_laps: list) -> str:
    """判断分析置信度：基于数据完整性"""
    score = 0

    # 有弯角数据
    if corners and len(corners) >= 5:
        score += 1
    # 有扇区数据
    if sectors and len(sectors) >= 2:
        score += 1
    # 有关键时刻数据
    if key_laps and len(key_laps) >= 2:
        score += 1

    if score >= 3:
        return 'high'
    elif score >= 2:
        return 'medium'
    else:
        return 'low'


def build_metrics(tel_a, tel_b, lap_a, lap_b, laps_a, laps_b,
                  driver_a: str, driver_b: str,
                  corner_distances: list, corner_labels: list) -> dict:
    """
    汇总所有维度指标，增强版。

    新增字段（增量添加，向后兼容）：
    - summary: 一句话概要（主导扇区、主要因素、置信度）
    - key_corners: 动态筛选的关键弯角（8-10个，替代llm_client中的固定筛选）
    - ideal_lap: 理想圈对比
    - fuel_corrected_pace: 燃油修正配速（仅正赛有意义）
    - tire_analysis: 增强版轮胎分析摘要
    """
    # 计算各项基础指标（保持向后兼容）
    all_corners = analyze_corners(tel_a, tel_b, corner_distances, corner_labels)
    sectors = analyze_sectors(lap_a, lap_b, driver_a, driver_b)
    straights = analyze_straights(tel_a, tel_b, driver_a, driver_b)
    tyre = analyze_tyre_stability(laps_a, laps_b, driver_a, driver_b)
    key_laps = identify_key_laps(laps_a, laps_b, driver_a, driver_b)
    stint_degradation = analyze_stint_degradation(laps_a, laps_b, driver_a, driver_b)

    # 动态筛选关键弯角
    key_corners = select_key_corners(all_corners)

    # 新增指标
    ideal_lap = calculate_ideal_lap(laps_a, laps_b, driver_a, driver_b)

    # 构建summary
    dominant_sector = _determine_dominant_sector(sectors)
    primary_factor = _determine_primary_factor(key_corners, straights, sectors, tyre)
    confidence = _determine_confidence(key_corners, sectors, key_laps)

    # 计算总差距
    try:
        lap_time_a = lap_a['LapTime']
        lap_time_b = lap_b['LapTime']
        if hasattr(lap_time_a, 'iloc'):
            lap_time_a = lap_time_a.iloc[0]
        if hasattr(lap_time_b, 'iloc'):
            lap_time_b = lap_time_b.iloc[0]
        delta_s = abs((lap_time_a - lap_time_b).total_seconds())
        gap_str = f"{delta_s:.3f}s"
    except Exception:
        gap_str = "N/A"

    summary = {
        "gap": gap_str,
        "dominant_sector": dominant_sector,
        "primary_factor": primary_factor,
        "confidence": confidence,
    }

    # 轮胎分析摘要
    tire_analysis = {
        "strategy_comparison": stint_degradation.get('strategy_comparison', 'unknown'),
        "degradation_comparison": {
            driver_a: stint_degradation.get(driver_a, []),
            driver_b: stint_degradation.get(driver_b, []),
        },
        "consistency_comparison": {
            driver_a: tyre.get(driver_a, {}),
            driver_b: tyre.get(driver_b, {}),
        },
    }

    result = {
        # 向后兼容字段（保持原有结构）
        "corners": all_corners,        # 全部弯角数据
        "sectors": sectors,
        "straights": straights,
        "tyre": tyre,
        "key_laps": key_laps,
        "stint_degradation": stint_degradation,
        # 增强字段
        "summary": summary,
        "key_corners": key_corners,     # 动态筛选的关键弯角
        "ideal_lap": ideal_lap,
        "tire_analysis": tire_analysis,
    }

    return result
