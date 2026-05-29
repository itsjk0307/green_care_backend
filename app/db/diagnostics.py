from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def mask_database_url(url: str) -> str:
    """Hide password in DATABASE_URL for logs."""
    return re.sub(r":([^:@/]+)@", r":***@", url, count=1)


def parse_database_url(url: str) -> dict[str, str | int | None]:
    """Parse async/sync PostgreSQL URL into host/port/database."""
    normalized = url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(normalized)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": (parsed.path or "").lstrip("/") or None,
        "user": parsed.username,
    }


async def fetch_runtime_database_info(engine: AsyncEngine) -> dict[str, str | int]:
    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT current_database(), COALESCE(inet_server_port(), 0)")
        )
        db_name, port = row.one()
    return {"database": str(db_name), "port": int(port)}
