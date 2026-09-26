from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query, status
from pymongo.database import Database

from app.database.connection import get_db
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseFilterParams,
    ExpenseResponse,
    ExpenseUpdate,
)
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/trips/{trip_id}/expenses", tags=["Expenses"])


@router.post("", response_model=ResponseEnvelope[ExpenseResponse], status_code=status.HTTP_201_CREATED)
async def create_expense(
    trip_id: str,
    expense_in: ExpenseCreate,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[ExpenseResponse]:
    """Add a new expense to a trip and automatically calculate split shares."""
    expense = ExpenseService.create_expense(db, trip_id, expense_in)
    return ResponseEnvelope[ExpenseResponse](
        data=expense,
        message=f"Expense '{expense.title}' created successfully.",
    )


@router.get("", response_model=ResponseEnvelope[PaginatedResponse[ExpenseResponse]])
async def list_expenses(
    trip_id: str,
    category: Optional[str] = Query(default=None, description="Filter by category"),
    paid_by: Optional[str] = Query(default=None, description="Filter by payer member ID"),
    date_from: Optional[datetime] = Query(default=None, description="Filter on or after date"),
    date_to: Optional[datetime] = Query(default=None, description="Filter on or before date"),
    min_amount: Optional[Decimal] = Query(default=None, ge=0, description="Minimum expense amount"),
    max_amount: Optional[Decimal] = Query(default=None, ge=0, description="Maximum expense amount"),
    sort_by: Literal["date", "amount"] = Query(default="date", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort direction"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Database = Depends(get_db),
) -> ResponseEnvelope[PaginatedResponse[ExpenseResponse]]:
    """List expenses for a trip with filtering, sorting, and pagination."""
    params = ExpenseFilterParams(
        category=category,
        paid_by=paid_by,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
    )
    paginated = ExpenseService.list_expenses(db, trip_id, params)
    return ResponseEnvelope[PaginatedResponse[ExpenseResponse]](
        data=paginated,
        message=f"Found {paginated.pagination.total} expenses.",
    )


@router.get("/{expense_id}", response_model=ResponseEnvelope[ExpenseResponse])
async def get_expense(
    trip_id: str,
    expense_id: str,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[ExpenseResponse]:
    """Retrieve an expense by ID."""
    expense = ExpenseService.get_expense(db, trip_id, expense_id)
    return ResponseEnvelope[ExpenseResponse](
        data=expense,
        message="Expense retrieved successfully.",
    )


@router.put("/{expense_id}", response_model=ResponseEnvelope[ExpenseResponse])
async def update_expense(
    trip_id: str,
    expense_id: str,
    expense_in: ExpenseUpdate,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[ExpenseResponse]:
    """Update an expense and recompute splits if amounts or shared members changed."""
    expense = ExpenseService.update_expense(db, trip_id, expense_id, expense_in)
    return ResponseEnvelope[ExpenseResponse](
        data=expense,
        message="Expense updated successfully.",
    )


@router.delete("/{expense_id}", response_model=ResponseEnvelope[dict])
async def delete_expense(
    trip_id: str,
    expense_id: str,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[dict]:
    """Delete an expense by ID."""
    ExpenseService.delete_expense(db, trip_id, expense_id)
    return ResponseEnvelope[dict](
        data={"expense_id": expense_id, "deleted": True},
        message="Expense deleted successfully.",
    )
