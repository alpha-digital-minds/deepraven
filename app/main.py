import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.redis_client import close_redis, get_redis
from app.supabase_client import close_supabase, get_supabase
from app.worker import compression_worker, extraction_worker
from app.routers import account_keys, auth, config, contacts, conversations, profiles, projects, stats

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis()
    await get_supabase()
    worker = asyncio.create_task(
        extraction_worker(delay_seconds=get_settings().extraction_delay_seconds)
    )
    compressor = asyncio.create_task(compression_worker(run_hour_utc=23))
    yield
    worker.cancel()
    compressor.cancel()
    await close_redis()
    await close_supabase()


app = FastAPI(
    title="DeepRaven",
    description="Long-lasting memory layer for sales agents — multi-tenant SaaS.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(account_keys.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(contacts.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/auth/confirm", include_in_schema=False)
async def auth_confirm_shortcut(request: Request) -> RedirectResponse:
    """Short URL that Supabase redirects to — forwards to the API handler."""
    qs = request.url.query
    return RedirectResponse(f"/api/v1/auth/confirm{'?' + qs if qs else ''}", status_code=302)


@app.get("/assets/logo.png", include_in_schema=False)
async def logo():
    return FileResponse(Path(__file__).parent / "assets" / "logo.png")


@app.get("/assets/raven.png", include_in_schema=False)
async def raven():
    return FileResponse(Path(__file__).parent / "assets" / "raven.png")


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve Vite-built assets (JS, CSS) — must be mounted BEFORE the SPA catch-all
# so /dashboard/assets/* is handled here rather than falling into the route below.
_dist = Path(__file__).parent / "static" / "dist"
if _dist.exists():
    app.mount("/dashboard/assets", StaticFiles(directory=str(_dist / "assets")), name="dashboard-assets")


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard/{path:path}", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(path: str = "") -> HTMLResponse:
    dist_index = Path(__file__).parent / "static" / "dist" / "index.html"
    return HTMLResponse(content=dist_index.read_text())
