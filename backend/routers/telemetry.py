from fastapi import APIRouter
from models.response import ok, err
from services.fastf1_service import (
    get_session, fmt_time, get_corner_distances, get_corner_labels, telemetry_to_dict
)
import fastf1.plotting
import numpy as np

router = APIRouter()

@router.get("")
def get_telemetry(
    year: int = 2026,
    round: int = None,
    event: str = None,
    d1: str = "ALB",
    d2: str = "ALO",
    session: str = "Q"
):
    try:
        identifier = round if round else event
        s = get_session(year, identifier, session)

        lap_a = s.laps.pick_drivers(d1).pick_fastest()
        lap_b = s.laps.pick_drivers(d2).pick_fastest()

        tel_a = lap_a.get_car_data().add_distance()
        tel_b = lap_b.get_car_data().add_distance()

        circuit_info = s.get_circuit_info()
        total_dist = max(tel_a['Distance'].max(), tel_b['Distance'].max())
        n_corners  = len(circuit_info.corners)
        corner_dist   = get_corner_distances(circuit_info, total_dist, n_corners)
        corner_labels = get_corner_labels(circuit_info)

        # 数据质量检查
        note = None
        dist_a = tel_a['Distance'].max()
        dist_b = tel_b['Distance'].max()
        if dist_a < total_dist * 0.97:
            note = f"{d1} telemetry truncated at {dist_a:.0f}m (expected ~{total_dist:.0f}m) — F1 API packet loss"
        elif dist_b < total_dist * 0.97:
            note = f"{d2} telemetry truncated at {dist_b:.0f}m (expected ~{total_dist:.0f}m) — F1 API packet loss"

        # 车队颜色
        try:
            color_a = fastf1.plotting.get_driver_color(d1, session=s)
            color_b = fastf1.plotting.get_driver_color(d2, session=s)
        except Exception:
            color_a, color_b = "#FFFFFF", "#FF8000"

        team_a = str(lap_a['Team']) if hasattr(lap_a['Team'], '__str__') else ""
        team_b = str(lap_b['Team']) if hasattr(lap_b['Team'], '__str__') else ""

        lap_time_a = lap_a['LapTime']
        lap_time_b = lap_b['LapTime']
        if hasattr(lap_time_a, 'iloc'):
            lap_time_a = lap_time_a.iloc[0]
        if hasattr(lap_time_b, 'iloc'):
            lap_time_b = lap_time_b.iloc[0]

        delta_s = (lap_time_a - lap_time_b).total_seconds()
        faster  = d1 if delta_s < 0 else d2
        gap     = f"{abs(delta_s):.3f}s ({faster} faster)"

        return ok({
            "driver_a": {"code": d1, "team": team_a, "color": color_a, "lap_time": fmt_time(lap_time_a)},
            "driver_b": {"code": d2, "team": team_b, "color": color_b, "lap_time": fmt_time(lap_time_b)},
            "gap": gap,
            "corner_labels":    corner_labels,
            "corner_distances": corner_dist,
            "telemetry": {
                d1: telemetry_to_dict(tel_a),
                d2: telemetry_to_dict(tel_b),
            }
        }, note=note)
    except Exception as e:
        return err(str(e))
