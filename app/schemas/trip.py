from datetime import date, datetime, timezone
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from app.utils.object_id import PyObjectId


class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Member's full or display name")
    email: Optional[EmailStr] = Field(default=None, description="Optional member email address")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Member name cannot be empty or whitespace only.")
        return trimmed


class MemberCreate(MemberBase):
    pass


class MemberResponse(MemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier for the member within the trip")
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when member joined")


class TripBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Trip name (e.g. Goa Trip)")
    destination: str = Field(..., min_length=1, max_length=200, description="Destination (e.g. Goa, India)")
    start_date: date = Field(..., description="Trip start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Trip end date (YYYY-MM-DD)")

    @field_validator("name", "destination")
    @classmethod
    def clean_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or whitespace only.")
        return trimmed

    @model_validator(mode="after")
    def validate_dates(self) -> "TripBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date.")
        return self


class TripCreate(TripBase):
    members: list[MemberCreate] = Field(
        ...,
        min_length=1,
        description="Initial members list. At least one member is required.",
    )

    @field_validator("members")
    @classmethod
    def validate_unique_members(cls, members: list[MemberCreate]) -> list[MemberCreate]:
        names = [m.name.lower() for m in members]
        if len(names) != len(set(names)):
            raise ValueError("Trip members must have unique names.")
        return members


class TripUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    destination: Optional[str] = Field(default=None, min_length=1, max_length=200)
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)

    @field_validator("name", "destination")
    @classmethod
    def clean_text_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Field cannot be empty or whitespace only.")
            return trimmed
        return v

    @model_validator(mode="after")
    def validate_dates_if_both_present(self) -> "TripUpdate":
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date cannot be earlier than start_date.")
        return self


class TripResponse(TripBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: PyObjectId = Field(..., validation_alias="_id", description="MongoDB ObjectId string")
    members: list[MemberResponse] = Field(default_factory=list, description="List of trip members")
    created_at: datetime = Field(..., description="Trip creation timestamp")
    updated_at: datetime = Field(..., description="Trip last updated timestamp")
