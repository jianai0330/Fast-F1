"""
FastF1 数据获取封装
所有对 FastF1 的调用统一走这里，方便缓存和错误处理
"""
import logging

import fastf1
import numpy as np
import pandas as pd
from fastf1.exceptions import DataNotLoadedError

logger = logging.getLogger(__name__)

# 进程级内存缓存：同一个 session 只 load 一次
_session_cache = {}

def get_session(year: int, round_or_name, session_type: str):
    """加载 session，内存缓存，同一进程内第二次请求直接返回

    如果 session.load() 之后 laps 数据不可用，记录日志但不崩溃，
    仍然返回 session 对象，由调用方通过 check_laps_available() 做进一步检查。
    """
    key = (year, str(round_or_name), session_type)
    if key not in _session_cache:
        session = fastf1.get_session(year, round_or_name, session_type)
        try:
            session.load()
        except Exception as e:
            logger.warning(f"session.load() 失败: {year} {round_or_name} {session_type} - {e}")
            _session_cache[key] = session
            return session
        # load 完成后检查 laps 是否真的可用
        try:
            _ = session.laps
        except DataNotLoadedError:
            logger.warning(
                f"session.laps 数据不可用: {year} {round_or_name} {session_type}"
            )
        _session_cache[key] = session
    return _session_cache[key]


def check_laps_available(session) -> str | None:
    """检查 session 的 laps 数据是否可用，返回 None 表示可用，否则返回中文错误提示"""
    try:
        _ = session.laps
        return None
    except DataNotLoadedError:
        return "该场次的详细计时数据暂未提供，可能是官方数据尚未发布，请稍后再试。"


def fmt_time(td) -> str:
    """timedelta → '1:28.123' 格式，去掉 '0 days' 前缀"""
    if pd.isna(td):
        return "N/A"
    if hasattr(td, 'iloc'):
        td = td.iloc[0]
    total_ms = int(td.total_seconds() * 1000)
    ms = total_ms % 1000
    total_s = total_ms // 1000
    m, s = divmod(total_s, 60)
    return f"{m}:{s:02d}.{ms:03d}"


def get_corner_distances(circuit_info, total_dist: float, n_corners: int) -> list:
    """
    获取弯角距离列表。
    2026赛季 circuit_info.corners['Distance'] 全为 NaN，自动等间距 fallback。
    """
    distances = circuit_info.corners['Distance'].values
    if np.isnan(distances).all():
        distances = np.linspace(0, total_dist, n_corners + 1)[1:]
    return distances.tolist()


def get_corner_labels(circuit_info) -> list:
    return [
        f"T{int(r['Number'])}{r['Letter']}"
        for _, r in circuit_info.corners.iterrows()
    ]


def telemetry_to_dict(tel) -> dict:
    """遥测 DataFrame → 可序列化 dict，处理 NaN"""
    return {
        "distance": tel['Distance'].round(1).tolist(),
        "speed":    tel['Speed'].fillna(0).round(1).tolist(),
        "throttle": tel['Throttle'].fillna(0).round(1).tolist(),
        "brake":    tel['Brake'].fillna(False).astype(int).tolist(),
        "gear":     tel['nGear'].fillna(0).astype(int).tolist(),
    }
