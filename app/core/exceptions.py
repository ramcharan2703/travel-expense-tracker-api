from typing import Any, Optional
from fastapi import status


class AppException(Exception):
    """Base application exception with HTTP status code and standardized error metadata."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class ResourceNotFoundException(AppException):
    def __init__(self, message: str, code: str = "RESOURCE_NOT_FOUND", details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class TripNotFoundError(ResourceNotFoundException):
    def __init__(self, trip_id: str) -> None:
        super().__init__(
            message=f"Trip with ID '{trip_id}' was not found.",
            code="TRIP_NOT_FOUND",
            details={"trip_id": trip_id},
        )


class ExpenseNotFoundError(ResourceNotFoundException):
    def __init__(self, expense_id: str) -> None:
        super().__init__(
            message=f"Expense with ID '{expense_id}' was not found.",
            code="EXPENSE_NOT_FOUND",
            details={"expense_id": expense_id},
        )


class MemberNotFoundError(ResourceNotFoundException):
    def __init__(self, member_id: str) -> None:
        super().__init__(
            message=f"Member with ID '{member_id}' was not found in this trip.",
            code="MEMBER_NOT_FOUND",
            details={"member_id": member_id},
        )


class BusinessRuleException(AppException):
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION", details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class InvalidMemberError(BusinessRuleException):
    def __init__(self, message: str, invalid_members: Optional[list[str]] = None) -> None:
        super().__init__(
            message=message,
            code="INVALID_MEMBER",
            details={"invalid_members": invalid_members} if invalid_members else None,
        )


class DatabaseConnectionException(AppException):
    def __init__(self, message: str = "Database service is temporarily unavailable.") -> None:
        super().__init__(
            message=message,
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
