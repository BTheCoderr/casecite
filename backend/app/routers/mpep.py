"""Development-only MPEP retrieval and opt-in local issue spotting."""

import asyncio
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Response
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.exceptions import NotFoundError, ServiceUnavailableError, UpstreamError
from app.services import mpep, mpep_analysis
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


class AnalysisRequest(SearchRequest):
    fictional_data_only: Literal[True]


@router.post("/analyze", response_model=mpep_analysis.AnalysisResult)
async def analyze_mpep(
    body: AnalysisRequest,
    response: Response,
    current_user: TokenData = require_permission("tools.research"),
) -> mpep_analysis.AnalysisResult:
    response.headers["Cache-Control"] = "no-store"
    index = await corpus()
    endpoint = settings.mpep_analysis_local_url
    model = settings.mpep_analysis_local_model
    # Only an explicitly configured loopback endpoint. No server or user API
    # keys, public provider fallback, redirects, or implicit paid model calls.
    url = urlsplit(endpoint)
    if (
        url.scheme != "http"
        or url.hostname not in ("127.0.0.1", "::1")
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path.rstrip("/") != "/v1"
        or not model
    ):
        raise ServiceUnavailableError("Configure an isolated loopback model for the preview")
    evidence = await asyncio.to_thread(mpep.search, index, body.query)
    if not evidence.hits:
        return mpep_analysis.AnalysisResult(issues=[], rejected=0, source_count=0)
    try:
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as transport:
            async with AsyncOpenAI(
                base_url=endpoint,
                api_key="not-needed",
                http_client=transport,
                timeout=60,
                max_retries=0,
            ) as client:
                return await mpep_analysis.draft_questions(
                    client, model, endpoint, body.query, evidence
                )
    except Exception:
        raise UpstreamError("Local patent analysis failed; no draft was accepted") from None
