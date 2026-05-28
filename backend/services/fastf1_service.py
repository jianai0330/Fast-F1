"""
FastF1 数据获取封装
所有对 FastF1 的调用统一走这里，方便缓存和错误处理
"""
import fastf1
import numpy as np
import pandas as pd
from functools import lru_cache


def get_session(year: int, round_or_name, session_type: str):
    """加载 session，自动使用 FastF1 缓存"""
    session = fastf1.get_session(year, round_or_name, session_type)
    session.load()
    return session


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
