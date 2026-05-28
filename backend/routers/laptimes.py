from fastapi import APIRouter
from models.response import ok, err
from services.fastf1_service import get_session, fmt_time

router = APIRouter()

@router.get("")
def get_laptimes(year: int = 2026, round: int = None, event: str = None, session: str = "R"):
    try:
        identifier = round if round else event
        s = get_session(year, identifier, session)

        drivers = s.laps['Driver'].unique().tolist()
        result = {}
        for drv in drivers:
            laps = s.laps.pick_drivers(drv).dropna(subset=['LapTime'])
            result[drv] = {
                "team":     laps['Team'].iloc[0] if len(laps) > 0 else "",
                "laps": [
                    {
                        "lap":      int(row['LapNumber']),
                        "time":     fmt_time(row['LapTime']),
                        "time_s":   round(row['LapTime'].total_seconds(), 3),
                        "compound": row.get('Compound', ''),
                        "tyre_life":int(row.get('TyreLife', 0)),
                        "pit_in":   bool(row.get('PitInTime') is not None and str(row.get('PitInTime')) != 'NaT'),
                        "pit_out":  bool(row.get('PitOutTime') is not None and str(row.get('PitOutTime')) != 'NaT'),
                    }
                    for _, row in laps.iterrows()
                ]
            }
        return ok({"event": s.event["EventName"], "year": year, "session": session, "drivers": result})
    except Exception as e:
        return err(str(e))
