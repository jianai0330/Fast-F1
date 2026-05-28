from pydantic import BaseModel
from typing import Any, Optional

class APIResponse(BaseModel):
    status: str = "ok"
    data: Any = None
    note: Optional[str] = None

def ok(data: Any, note: str = None) -> dict:
    return {"status": "ok", "data": data, "note": note}

def err(msg: str) -> dict:
    return {"status": "error", "data": None, "note": msg}
