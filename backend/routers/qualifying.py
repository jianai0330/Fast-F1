from fastapi import APIRouter
from models.response import ok, err
from services.fastf1_service import get_session, fmt_time

router = APIRouter()

@router.get("")
def get_qualifying(year: int = 2026, round: int = None, event: str = None):
    try:
        identifier = round if round else event
        session = get_session(year, identifier, 'Q')

        results = []
        for _, row in session.results.iterrows():
            results.append({
                "position": int(row.get("Position", 0)) if not str(row.get("Position", "")).strip() == "" else None,
                "driver":   row.get("Abbreviation", ""),
                "team":     row.get("TeamName", ""),
                "q1":       fmt_time(row.get("Q1")) if "Q1" in row else "N/A",
                "q2":       fmt_time(row.get("Q2")) if "Q2" in row else "N/A",
                "q3":       fmt_time(row.get("Q3")) if "Q3" in row else "N/A",
            })
        return ok({
            "event": session.event["EventName"],
            "year":  year,
            "results": results
        })
    except Exception as e:
        return err(str(e))
