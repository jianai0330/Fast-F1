from fastapi import APIRouter
from models.response import ok, err
import fastf1

router = APIRouter()

@router.get("")
def get_events(year: int = 2026):
    try:
        schedule = fastf1.get_event_schedule(year)
        events = []
        for _, row in schedule.iterrows():
            events.append({
                "round":      int(row.get("RoundNumber", 0)),
                "name":       row.get("EventName", ""),
                "country":    row.get("Country", ""),
                "location":   row.get("Location", ""),
                "date":       str(row.get("EventDate", ""))[:10],
                "format":     row.get("EventFormat", ""),
            })
        return ok(events)
    except Exception as e:
        return err(str(e))
