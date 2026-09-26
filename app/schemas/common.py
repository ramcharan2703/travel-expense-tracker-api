from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ResponseEnvelope(BaseModel, Generic[DataT]):
    """Standardized top-level success response envelope."""
    success: bool = Field(default=True, description="Indicates request success status")
    data: Optional[DataT] = Field(default=None, description="Response payload")
    message: str = Field(default="Operation completed successfully", description="User-facing status message")


class ErrorDetail(BaseModel):
    """Detailed error structure."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Any] = Field(default=None, description="Optional extra error context or validation errors")


class ErrorEnvelope(BaseModel):
    """Standardized top-level failure response envelope."""
    success: bool = Field(default=False, description="Always false for errors")
    error: ErrorDetail = Field(..., description="Structured error information")


class PaginationMetadata(BaseModel):
    """Metadata accompanying paginated list responses."""
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total matching items across all pages")
    pages: int = Field(..., ge=0, description="Total number of available pages")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated collection response."""
    items: list[DataT] = Field(default_factory=list, description="List of items for the requested page")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")
