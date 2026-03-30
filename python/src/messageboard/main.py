"""MessageBoard FastAPI Server."""

import os
from typing import Annotated, Optional

from fastapi import APIRouter, FastAPI, Header, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.requests import Request

from messageboard import __version__
from messageboard.authentication import InMemoryAuthentication
from messageboard.errors import APIError, Error
from messageboard.messages import InMemoryMessageDB
from messageboard.token import ACCESS_TOKEN_EXPIRE_MINUTES, JWTHandler

# ============================================================================
# App
# ============================================================================

_DOMAIN = os.environ.get("DOMAIN", "http://localhost:8000")
_MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES", "100"))

app = FastAPI(
    title="MessageBoard API",
    description="REST-API Schulungsserver — ein einfaches MessageBoard mit JWT-Authentifizierung",
    version=__version__,
    servers=[{"url": _DOMAIN, "description": "Server"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globale Instanzen (In-Memory, kein DI-Framework)
_SECRET = os.environ.get("SECRET_KEY", "change-me-in-production")
auth = InMemoryAuthentication(secret=_SECRET)
jwt_handler = JWTHandler(secret=_SECRET)
public_board = InMemoryMessageDB(check_author=False, max_messages=_MAX_MESSAGES)   # /api/v1/public/messages
auth_board   = InMemoryMessageDB(check_author=True, max_messages=_MAX_MESSAGES)    # /api/v1/messages

api = APIRouter(prefix="/api/v1")


# ============================================================================
# Pydantic-Schemas
# ============================================================================

class PublicMessageCreate(BaseModel):
    author:  str = Field(min_length=1, max_length=50)
    title:   str = Field(max_length=200)
    content: str = Field(min_length=1, max_length=1000)

class MessageCreate(BaseModel):
    title:   str = Field(max_length=200)
    content: str = Field(min_length=1, max_length=1000)

class PublicMessagePatch(BaseModel):
    author:  str = Field(min_length=1, max_length=50)
    title:   Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=1000)

class MessagePatch(BaseModel):
    title:   Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=1000)

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=5)

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ResetRequest(BaseModel):
    password: str


# ============================================================================
# Serialisierungs-Helper
# ============================================================================

def _etag(msg) -> str:
    ts = msg.updated_at or msg.created_at
    return '"' + ts.isoformat() + '"'


def _token_out(username: str) -> dict:
    return {
        "access_token":  jwt_handler.create_auth_token(username),
        "refresh_token": jwt_handler.create_refresh_token(username),
        "token_type":    "bearer",
        "expires_in":    ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ============================================================================
# Fehlerbehandlung
# ============================================================================

@app.exception_handler(APIError)
async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    """Mappt alle APIError-Subklassen auf den richtigen HTTP-Statuscode + JSON-Body."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ============================================================================
# Auth-Helper
# ============================================================================

def _require_auth(authorization: str | None) -> str:
    """Authorization-Header → Nutzername. Wirft InvalidTokenError (401) wenn fehlt/ungültig."""
    if not authorization or not authorization.startswith("Bearer "):
        raise Error.MISSING_AUTH_HEADER()
    return jwt_handler.check_auth_token(authorization[7:])


# ============================================================================
# Root & Health
# ============================================================================

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "version": __version__}


# ============================================================================
# Öffentlich — /api/v1/public/messages
# ============================================================================

@api.get(
    "/public/messages",
    tags=["Öffentlich"],
    summary="Alle öffentlichen Nachrichten auflisten",
)
async def list_public_messages(
    limit:  Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)]         = 0,
):
    return public_board.get_messages(limit=limit, offset=offset).to_dict()


@api.post(
    "/public/messages",
    tags=["Öffentlich"],
    summary="Öffentliche Nachricht erstellen",
    status_code=201,
)
async def create_public_message(body: PublicMessageCreate):
    msg = public_board.add_message(author=body.author, title=body.title, content=body.content)
    return JSONResponse(
        status_code=201,
        content=msg.to_dict(),
        headers={"Location": f"/api/v1/public/messages/{msg.id}"},
    )


@api.get(
    "/public/messages/{message_id}",
    tags=["Öffentlich"],
    summary="Einzelne öffentliche Nachricht abrufen",
)
async def get_public_message(
    message_id:    Annotated[int, Path(ge=1)],
    if_none_match: Annotated[str | None, Header()] = None,
):
    msg = public_board.get_message(message_id)
    etag = _etag(msg)
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return JSONResponse(content=msg.to_dict(), headers={"ETag": etag})


@api.put(
    "/public/messages/{message_id}",
    tags=["Öffentlich"],
    summary="Öffentliche Nachricht vollständig ersetzen (PUT)",
)
async def replace_public_message(message_id: Annotated[int, Path(ge=1)], body: PublicMessageCreate):
    msg = public_board.replace_message(message_id, author=body.author, title=body.title, content=body.content)
    return msg.to_dict()


@api.patch(
    "/public/messages/{message_id}",
    tags=["Öffentlich"],
    summary="Öffentliche Nachricht teilweise aktualisieren",
)
async def patch_public_message(message_id: Annotated[int, Path(ge=1)], body: PublicMessagePatch):
    msg = public_board.patch_message(message_id, author=body.author, content=body.content, title=body.title)
    return msg.to_dict()


@api.delete(
    "/public/messages/{message_id}",
    tags=["Öffentlich"],
    summary="Öffentliche Nachricht löschen",
    status_code=204,
)
async def delete_public_message(message_id: Annotated[int, Path(ge=1)]):
    public_board.delete_message(message_id, author="")


# ============================================================================
# Nachrichten — /api/v1/messages
# ============================================================================

@api.get(
    "/messages",
    tags=["Nachrichten"],
    summary="Alle Nachrichten auflisten",
)
async def list_messages(
    limit:  Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)]         = 0,
):
    return auth_board.get_messages(limit=limit, offset=offset).to_dict()


@api.post(
    "/messages",
    tags=["Nachrichten"],
    summary="Neue Nachricht erstellen",
    status_code=201,
)
async def create_message(
    body:          MessageCreate,
    authorization: Annotated[str | None, Header()] = None,
):
    user = _require_auth(authorization)
    msg = auth_board.add_message(author=user, title=body.title, content=body.content)
    return JSONResponse(
        status_code=201,
        content=msg.to_dict(),
        headers={"Location": f"/api/v1/messages/{msg.id}"},
    )


@api.get(
    "/messages/{message_id}",
    tags=["Nachrichten"],
    summary="Einzelne Nachricht abrufen",
)
async def get_message(
    message_id:    Annotated[int, Path(ge=1)],
    if_none_match: Annotated[str | None, Header()] = None,
):
    msg = auth_board.get_message(message_id)
    etag = _etag(msg)
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return JSONResponse(content=msg.to_dict(), headers={"ETag": etag})


@api.put(
    "/messages/{message_id}",
    tags=["Nachrichten"],
    summary="Nachricht vollständig ersetzen (PUT)",
)
async def replace_message(
    message_id:    Annotated[int, Path(ge=1)],
    body:          MessageCreate,
    authorization: Annotated[str | None, Header()] = None,
):
    user = _require_auth(authorization)
    msg = auth_board.replace_message(message_id, author=user, title=body.title, content=body.content)
    return msg.to_dict()


@api.patch(
    "/messages/{message_id}",
    tags=["Nachrichten"],
    summary="Nachricht teilweise aktualisieren (PATCH)",
)
async def patch_message(
    message_id:    Annotated[int, Path(ge=1)],
    body:          MessagePatch,
    authorization: Annotated[str | None, Header()] = None,
):
    user = _require_auth(authorization)
    msg = auth_board.patch_message(message_id, author=user, content=body.content, title=body.title)
    return msg.to_dict()


@api.delete(
    "/messages/{message_id}",
    tags=["Nachrichten"],
    summary="Nachricht löschen",
    status_code=204,
)
async def delete_message(
    message_id:    Annotated[int, Path(ge=1)],
    authorization: Annotated[str | None, Header()] = None,
):
    user = _require_auth(authorization)
    auth_board.delete_message(message_id, author=user)


# ============================================================================
# Authentifizierung — /api/v1/auth
# ============================================================================

@api.post(
    "/auth/register",
    tags=["Authentifizierung"],
    summary="Neuen Benutzer registrieren",
    status_code=201,
)
async def register(body: RegisterRequest):
    auth.add_user(body.username, body.password)
    return _token_out(body.username)


@api.post(
    "/auth/login",
    tags=["Authentifizierung"],
    summary="Einloggen und Token erhalten",
)
async def login(body: LoginRequest):
    canonical = body.username.lower().strip()
    auth.check_password(canonical, body.password)
    return _token_out(canonical)


@api.post(
    "/auth/refresh",
    tags=["Authentifizierung"],
    summary="Access Token erneuern",
)
async def refresh_token(body: RefreshRequest):
    new_access = jwt_handler.refresh_auth_token(body.refresh_token)
    return {
        "access_token":  new_access,
        "refresh_token": body.refresh_token,  # Refresh Token bleibt gleich
        "token_type":    "bearer",
        "expires_in":    ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@api.post(
    "/auth/logout",
    tags=["Authentifizierung"],
    summary="Ausloggen und Refresh Token invalidieren",
    status_code=204,
)
async def logout(
    _body:         RefreshRequest,   # per Spec erwartet; wir invalidieren alle Tokens des Users
    authorization: Annotated[str | None, Header()] = None,
):
    user = _require_auth(authorization)
    jwt_handler.invalidate_refresh_token(user)


# ============================================================================
# Admin
# ============================================================================

@api.post(
    "/admin/reset",
    tags=["Admin"],
    summary="Datenbank zurücksetzen",
    status_code=204,
)
async def reset_database(body: ResetRequest):
    """**NUR FÜR SCHULUNG**: In Produktion niemals verwenden!"""
    expected = os.environ.get("RESET_PASSWORD")
    if not expected or body.password != expected:
        raise Error.INVALID_RESET_PASSWORD()

    public_board.reset()
    auth_board.reset()
    auth.reset()
    jwt_handler.reset()


# ============================================================================
# Router einbinden & statische Dateien (muss nach allen Routen stehen)
# ============================================================================

app.include_router(api)

app.mount("/", StaticFiles(directory="quarto/_site", html=True), name="docs")
