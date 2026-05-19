from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """JSON body for POST /api/v1/auth/login only (not registration)."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=1, description="Account email")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str

