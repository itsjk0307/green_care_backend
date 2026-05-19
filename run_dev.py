"""Run the API from .env: API_BIND_HOST, API_PORT (no long uvicorn CLI each time)."""

from __future__ import annotations

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    print(
        f"[run_dev] Binding {settings.API_BIND_HOST}:{settings.API_PORT} "
        "(set API_BIND_HOST / API_PORT in .env)"
    )
    if settings.DEV_API_PUBLIC_URL:
        base = settings.DEV_API_PUBLIC_URL.rstrip("/")
        print(f"[run_dev] Mobile: set EXPO_PUBLIC_API_URL={base}")
        print(f"[run_dev] Swagger (LAN): {base}/docs")
    else:
        print(
            "[run_dev] Tip: set DEV_API_PUBLIC_URL in .env (e.g. http://192.168.0.61:8000) "
            "and use the same value in golf-disease-mobile/.env"
        )

    uvicorn.run(
        "app.main:app",
        host=settings.API_BIND_HOST,
        port=settings.API_PORT,
        reload=True,
    )
