from fastapi import APIRouter

from wr3_api.services.integrations import IntegrationStatusService

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])


@router.get("/status")
async def integration_status() -> dict[str, object]:
    return IntegrationStatusService().summary()
