import logging
import os
import socket
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.db.seed import seed_golf_courses
from app.db.session import AsyncSessionLocal, engine
from app.schemas.common import ApiResponse, HealthCheckData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Create App ───────────────────────────────────────
app = FastAPI(
    title="GreenCare API",
    description="GreenCare - Smart Golf Course Management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Create Storage Folders ───────────────────────────
Path("storage/images/reports").mkdir(parents=True, exist_ok=True)
Path("storage/images/detections").mkdir(parents=True, exist_ok=True)
Path("storage/maps").mkdir(parents=True, exist_ok=True)

# ─── CORS Middleware (must be first!) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request Logging Middleware ────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    
    print(f"\n>>> {request.method} {request.url.path}")
    
    body_bytes = await request.body()
    if body_bytes:
        try:
            print(f"    Body: {body_bytes.decode('utf-8')[:200]}")
        except Exception:
            pass

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False
        }

    new_request = Request(request.scope, receive)
    
    try:
        response = await call_next(new_request)
    except Exception as e:
        import traceback
        print(f"    ERROR in middleware: {e}")
        traceback.print_exc()
        raise

    duration = (time.time() - start) * 1000
    print(f"<<< {response.status_code} ({duration:.0f}ms)")
    
    return response

# ─── Exception Handlers ───────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = []
    for err in exc.errors():
        loc = ".".join(str(i) for i in err.get("loc", []))
        msg = err.get("msg", "Invalid value.")
        details.append(f"{loc}: {msg}" if loc else msg)
    message = " | ".join(details)
    print(f"    VALIDATION ERROR: {message}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": message,
            "data": None
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    import traceback
    print(f"\n!!! GLOBAL ERROR: {type(exc).__name__}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"{type(exc).__name__}: {str(exc)}",
            "data": None,
        },
    )

# ─── Health Check ─────────────────────────────────────
@app.get("/health")
async def health_check():
    database = "disconnected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        database = "connected"
    except Exception as e:
        print(f"DB health check failed: {e}")

    return {
        "success": True,
        "message": "Service is healthy.",
        "data": {
            "status": "ok",
            "version": "2.0.0",
            "database": database,
            "modules": [
                "auth",
                "work_reports",
                "detections",
                "golf_courses",
                "map_areas",
                "daily_plans",
            ]
        }
    }

# ─── API Routes ───────────────────────────────────────
app.include_router(api_v1_router, prefix="/api/v1")

# ─── Static Files (AFTER routes!) ─────────────────────
app.mount(
    "/storage",
    StaticFiles(directory="storage"),
    name="storage",
)

# ─── Startup Event ────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "localhost"

    port = settings.API_PORT
    stable = (settings.DEV_API_PUBLIC_URL or "").rstrip("/")
    print("=" * 50)
    print("[*] GREENCARE API STARTED")
    print("=" * 50)
    if stable:
        print(f"Stable URL (mobile / Swagger): {stable}")
        print(f"  Swagger: {stable}/docs")
        print(f"  ReDoc:   {stable}/redoc")
    print(f"Local:   http://127.0.0.1:{port}")
    print(f"Network: http://{local_ip}:{port}")
    if not stable:
        print(f"Swagger: http://127.0.0.1:{port}/docs")
        print(f"ReDoc:   http://127.0.0.1:{port}/redoc")
    print("(Set API_PORT + DEV_API_PUBLIC_URL in .env; use python run_dev.py to match.)")
    print("=" * 50)

    async with AsyncSessionLocal() as db:
        await seed_golf_courses(db)

    print("[OK] GreenCare API ready!")
