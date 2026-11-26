"""Development-only MPEP corpus retrieval; no network access or AI calls."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.exceptions import NotFoundError, ServiceUnavailableError
from app.services import mpep
from app.services.auth import TokenData
from app.services.permissions import require_permission

router = APIRouter(prefix="/ip-research", tags=["ip-research"])


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=200)


class VerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section: str = Field(max_length=12)
    sha256: str = Field(min_length=64, max_length=64)
    quote: str = Field(min_length=12, max_length=1200)


class VerifyResponse(BaseModel):
    matches_indexed_text: bool


async def corpus() -> mpep.Corpus:
    if not settings.debug or not settings.mpep_preview_corpus:
        raise NotFoundError("MPEP corpus preview is unavailable")
    try:
        return await asyncio.to_thread(mpep.load_corpus, Path(settings.mpep_preview_corpus))
    except (ValueError, OSError):
        raise ServiceUnavailableError("No valid reviewed MPEP corpus is installed") from None


@router.post("/search", response_model=mpep.SearchResult)
async def search_mpep(
    body: SearchRequest,
    response: Response,
    current_user: TokenData = require_permission("tools.research"),
) -> mpep.SearchResult:
    response.headers["Cache-Control"] = "no-store"
    index = await corpus()
    return await asyncio.to_thread(mpep.search, index, body.query)


@router.post("/verify", response_model=VerifyResponse)
async def verify_mpep(
    body: VerifyRequest,
    response: Response,
    current_user: TokenData = require_permission("tools.research"),
) -> VerifyResponse:
    response.headers["Cache-Control"] = "no-store"
    index = await corpus()
    return VerifyResponse(
        matches_indexed_text=await asyncio.to_thread(
            mpep.verify, index, body.section, body.sha256, body.quote
        )
    )
