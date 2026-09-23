"""
snapclip3 — URL shortener with a paid tier.

Free tier: shorten a URL with an auto-generated short code, and redirect.
Paid tier (requires license key via entitlements.require_pro):
  - custom aliases
  - click analytics dashboard
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional

from storage import (
    init_db,
    create_short_link,
    get_link,
    register_click,
    get_click_history,
)
from entitlements import require_pro

app = FastAPI(title="snapclip3", description="URL shortener with a paid tier")


@app.on_event("startup")
def _startup():
    init_db()


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    target_url: str


class CustomShortenRequest(BaseModel):
    url: HttpUrl
    alias: str


# ---------------------------------------------------------------------------
# FREE / TRIAL ENDPOINT — anyone can shorten a URL with an auto-generated code
# ---------------------------------------------------------------------------
@app.post("/shorten", response_model=ShortenResponse)
def shorten_url(payload: ShortenRequest, request: Request):
    code = create_short_link(str(payload.url))
    base = str(request.base_url).rstrip("/")
    return ShortenResponse(
        code=code, short_url=f"{base}/r/{code}", target_url=str(payload.url)
    )


@app.get("/r/{code}")
def redirect_short_link(code: str, request: Request):
    link = get_link(code)
    if not link:
        raise HTTPException(status_code=404, detail="Short link not found")
    register_click(code, referrer=request.headers.get("referer"))
    return RedirectResponse(url=link["target_url"])


# ---------------------------------------------------------------------------
# PAID ENDPOINTS — require a valid license key
# ---------------------------------------------------------------------------
@app.post("/pro/shorten-custom", response_model=ShortenResponse)
def shorten_url_custom(
    payload: CustomShortenRequest,
    request: Request,
    _license=Depends(require_pro),
):
    try:
        code = create_short_link(str(payload.url), custom_alias=payload.alias)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    base = str(request.base_url).rstrip("/")
    return ShortenResponse(
        code=code, short_url=f"{base}/r/{code}", target_url=str(payload.url)
    )


@app.get("/pro/analytics/{code}")
def link_analytics(code: str, _license=Depends(require_pro)):
    link = get_link(code)
    if not link:
        raise HTTPException(status_code=404, detail="Short link not found")
    history = get_click_history(code)
    return {
        "code": code,
        "target_url": link["target_url"],
        "click_count": link["click_count"],
        "created_at": link["created_at"],
        "recent_clicks": history[:50],
    }


@app.get("/")
def root():
    return {
        "service": "snapclip3",
        "free_tier": "POST /shorten, GET /r/{code}",
        "paid_tier": "POST /pro/shorten-custom, GET /pro/analytics/{code} "
        "(requires X-License-Key header)",
    }
