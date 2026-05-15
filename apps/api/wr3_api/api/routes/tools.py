from __future__ import annotations

from fastapi import APIRouter

from wr3_api.services.tools import ToolStatusService

router = APIRouter(prefix="/v1/tools", tags=["tools"])
service = ToolStatusService()


@router.get("/status")
async def get_tools_status():
    return service.summary()
