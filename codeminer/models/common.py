"""Common data models and types."""

from datetime import datetime
from pydantic import BaseModel, Field

from ..datetime_utils import utc_now


class BaseResponse(BaseModel):
    """Base response model with common fields."""

    pass


class TimestampMixin(BaseModel):
    """Mixin for models with timestamp fields."""

    created_at: datetime = Field(
        default_factory=utc_now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=utc_now, description="Last update timestamp"
    )


class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    items: list
    total: int
    page: int = 1
    page_size: int = 100
