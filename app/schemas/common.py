from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthCheckData(BaseModel):
    status: str
    version: str
    modules: list[str]
    database: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T
