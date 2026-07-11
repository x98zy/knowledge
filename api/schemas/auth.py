from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Login success response body."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Token refresh request body."""

    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Token refresh success response body."""

    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    """Change password request body."""

    old_password: str = Field(..., description="Old password")
    new_password: str = Field(..., description="New password")
