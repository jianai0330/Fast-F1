from fastapi import APIRouter
from models.response import ok, err
from services.fastf1_service import get_session, fmt_time

router = APIRouter()

@router.get("")
def get_qualifying(year: int = 2026, round_num: int = None, event: str = None):
    try:
        identifier = round_num if round_num else event
        session = get_session(year, identifier, 'Q')

        results = []
        for _, row in session.results.iterrows():
            results.append({
                "position": int(row["Position"]) if "Position" in row and row["Position"] == row["Position"] else None,
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
