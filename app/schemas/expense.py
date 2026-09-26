from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.utils.object_id import PyObjectId

# Standard recommended expense categories
STANDARD_CATEGORIES = [
    "Food",
    "Travel",
    "Accommodation",
    "Shopping",
    "Entertainment",
    "Tickets",
    "Other",
]


class SplitShare(BaseModel):
    """Calculated split share for an individual member."""
    model_config = ConfigDict(from_attributes=True)

    member_id: str = Field(..., description="ID of the member")
    share: Decimal = Field(..., gt=0, decimal_places=2, description="Member's computed share amount")


class ExpenseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Expense title (e.g. Seafood Dinner)")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Total amount paid (> 0.00)")
    category: str = Field(default="Other", min_length=1, max_length=50, description="Expense category")
    paid_by: str = Field(..., min_length=1, description="ID of the member who paid")
    shared_by: list[str] = Field(
        ...,
        min_length=1,
        description="List of member IDs sharing this expense. At least one member is required.",
    )
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Expense timestamp")
    description: Optional[str] = Field(default=None, max_length=500, description="Optional notes or description")

    @field_validator("title", "category", "paid_by")
    @classmethod
    def clean_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or whitespace only.")
        return trimmed

    @field_validator("category")
    @classmethod
    def format_category(cls, v: str) -> str:
        trimmed = v.strip()
        # Auto-match standard category case-insensitively
        for std in STANDARD_CATEGORIES:
            if std.lower() == trimmed.lower():
                return std
        return trimmed.title()

    @field_validator("shared_by")
    @classmethod
    def validate_unique_shared_members(cls, v: list[str]) -> list[str]:
        cleaned = [m.strip() for m in v if m.strip()]
        if not cleaned:
            raise ValueError("shared_by must contain at least one valid member ID.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("shared_by contains duplicate member IDs.")
        return cleaned

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0.00"):
            raise ValueError("Amount must be strictly greater than 0.00.")
        # Normalize to 2 decimal places
        return v.quantize(Decimal("0.01"))


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    paid_by: Optional[str] = Field(default=None, min_length=1)
    shared_by: Optional[list[str]] = Field(default=None, min_length=1)
    date: Optional[datetime] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("title", "category", "paid_by")
    @classmethod
    def clean_text_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Field cannot be empty or whitespace only.")
            return trimmed
        return v

    @field_validator("shared_by")
    @classmethod
    def validate_unique_shared_members_optional(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            cleaned = [m.strip() for m in v if m.strip()]
            if not cleaned:
                raise ValueError("shared_by must contain at least one valid member ID.")
            if len(cleaned) != len(set(cleaned)):
                raise ValueError("shared_by contains duplicate member IDs.")
            return cleaned
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount_precision_optional(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= Decimal("0.00"):
                raise ValueError("Amount must be strictly greater than 0.00.")
            return v.quantize(Decimal("0.01"))
        return v


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: PyObjectId = Field(..., validation_alias="_id", description="Expense ObjectId string")
    trip_id: PyObjectId = Field(..., description="Parent Trip ObjectId string")
    split_shares: list[SplitShare] = Field(default_factory=list, description="Computed individual split shares")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")


class ExpenseFilterParams(BaseModel):
    """Query parameters for filtering, sorting, and paginating trip expenses."""
    category: Optional[str] = Field(default=None, description="Filter by category (e.g. Food)")
    paid_by: Optional[str] = Field(default=None, description="Filter by member ID who paid")
    date_from: Optional[datetime] = Field(default=None, description="Filter expenses on or after this timestamp")
    date_to: Optional[datetime] = Field(default=None, description="Filter expenses on or before this timestamp")
    min_amount: Optional[Decimal] = Field(default=None, ge=0, description="Minimum expense amount")
    max_amount: Optional[Decimal] = Field(default=None, ge=0, description="Maximum expense amount")
    sort_by: Literal["date", "amount"] = Field(default="date", description="Field to sort by")
    sort_order: Literal["asc", "desc"] = Field(default="desc", description="Sort direction")
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
