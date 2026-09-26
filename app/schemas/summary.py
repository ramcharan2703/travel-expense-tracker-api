from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.utils.object_id import PyObjectId


class MemberFinancialSummary(BaseModel):
    """Financial standing of an individual member within a trip."""
    model_config = ConfigDict(from_attributes=True)

    member_id: str = Field(..., description="Unique member identifier")
    member_name: str = Field(..., description="Member display name")
    total_paid: Decimal = Field(..., decimal_places=2, description="Total amount paid by member")
    total_share: Decimal = Field(..., decimal_places=2, description="Total share owed by member")
    balance: Decimal = Field(..., decimal_places=2, description="Net balance (total_paid - total_share)")
    owes: Decimal = Field(..., decimal_places=2, description="Amount member needs to pay to settle")
    receives: Decimal = Field(..., decimal_places=2, description="Amount member should receive to settle")


class CategorySummary(BaseModel):
    """Category breakdown of trip expenses."""
    category: str = Field(..., description="Expense category")
    total_amount: Decimal = Field(..., decimal_places=2, description="Total spent in this category")
    count: int = Field(..., ge=0, description="Number of expenses in this category")
    percentage: Decimal = Field(..., decimal_places=2, description="Percentage of total trip spend")


class TripSummaryResponse(BaseModel):
    """Aggregated financial summary of a trip."""
    trip_id: PyObjectId = Field(..., description="Trip ObjectId string")
    trip_name: str = Field(..., description="Trip name")
    total_trip_expenses: Decimal = Field(..., decimal_places=2, description="Total sum of all trip expenses")
    total_expenses_count: int = Field(..., ge=0, description="Total number of recorded expenses")
    members_summary: list[MemberFinancialSummary] = Field(default_factory=list, description="Per-member breakdown")
    category_breakdown: list[CategorySummary] = Field(default_factory=list, description="Per-category breakdown")


class SettlementTransaction(BaseModel):
    """A direct payment instruction from a debtor to a creditor."""
    debtor_id: str = Field(..., description="Member ID who pays the money")
    debtor_name: str = Field(..., description="Member name who pays")
    creditor_id: str = Field(..., description="Member ID who receives the money")
    creditor_name: str = Field(..., description="Member name who receives")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Exact transfer amount")


class TripSettlementResponse(BaseModel):
    """List of minimized transactions to settle all debts in the trip."""
    trip_id: PyObjectId = Field(..., description="Trip ObjectId string")
    trip_name: str = Field(..., description="Trip name")
    total_transactions: int = Field(..., ge=0, description="Number of transactions needed to settle")
    transactions: list[SettlementTransaction] = Field(default_factory=list, description="Ordered settlement instructions")
