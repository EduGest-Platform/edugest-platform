"""Draft API contract, deliberately separate from the live OpenAPI until approved."""

import json
from pathlib import Path

from fastapi import FastAPI

from app.modules.learning.attendance_router import router

OUT = Path(__file__).resolve().parents[2] / "contracts/proposed/attendance.openapi.json"


def render() -> str:
    candidate = FastAPI(title="PROPOSED academic attendance contract", version="0.0.0-proposed")
    candidate.include_router(router, prefix="/api/v1")
    spec = candidate.openapi()
    spec["x-status"] = "PROPOSED_NOT_MOUNTED"
    return json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print("Wrote proposed attendance contract (not mounted in live app)")
