from __future__ import annotations

from typing import Annotated

from fastapi import Header

from wr3_api.services.auth import AuthContext, AuthService

auth_service = AuthService()


async def get_optional_auth(
    authorization: Annotated[str | None, Header()] = None,
    x_wr3_user: Annotated[str | None, Header()] = None,
    x_wr3_reviewer: Annotated[str | None, Header()] = None,
) -> AuthContext:
    return auth_service.context_from_headers(
        authorization=authorization,
        x_wr3_user=x_wr3_user,
        x_wr3_reviewer=x_wr3_reviewer,
    )
