from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthCheckData(BaseModel):
    status: str
    version: str
    modules: list[str]
    database: str
    database_name: str | None = None
    database_port: int | None = None
    database_url_masked: str | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T
