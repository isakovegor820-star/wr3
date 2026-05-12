from fastapi import APIRouter

from wr3_api.api.routes.audits import service
from wr3_api.domain.enums import Chain

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("/{chain}/{address}")
async def get_project(chain: Chain, address: str):
    return service.public_project(chain, address)
