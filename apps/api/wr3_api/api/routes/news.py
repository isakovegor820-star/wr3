from fastapi import APIRouter, HTTPException, Query

from wr3_api.services.news import NewsIngestionService

router = APIRouter(prefix="/v1/news", tags=["news"])


@router.get("/hacks")
async def list_hacks(limit: int = Query(default=25, ge=1, le=100)) -> dict[str, object]:
    try:
        return await NewsIngestionService().fetch_defillama_hacks(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"defillama_hacks_fetch_failed:{exc.__class__.__name__}") from exc
