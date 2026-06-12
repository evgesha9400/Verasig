from fastapi import APIRouter, Request
from sqlalchemy import select

router = APIRouter()


@router.get("/health")
def read_health(request: Request) -> dict[str, str]:
    with request.app.state.session_factory() as session:
        session.execute(select(1)).scalar_one()
    return {"status": "ok"}
