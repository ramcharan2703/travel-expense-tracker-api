from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.database.connection import get_db
from app.schemas.common import ResponseEnvelope
from app.schemas.summary import TripSettlementResponse, TripSummaryResponse
from app.services.settlement_service import SettlementService

router = APIRouter(prefix="/trips/{trip_id}", tags=["Settlements & Summary"])


@router.get("/summary", response_model=ResponseEnvelope[TripSummaryResponse])
async def get_trip_summary(
    trip_id: str,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[TripSummaryResponse]:
    """
    Get full financial summary of a trip, including:
    - Total expenses and count
    - Category breakdown (totals and percentages)
    - Per-member balances (total paid, total share owed, net balance)
    """
    summary = SettlementService.get_trip_summary(db, trip_id)
    return ResponseEnvelope[TripSummaryResponse](
        data=summary,
        message="Trip financial summary generated successfully.",
    )


@router.get("/settlement", response_model=ResponseEnvelope[TripSettlementResponse])
async def get_trip_settlement(
    trip_id: str,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[TripSettlementResponse]:
    """
    Compute optimal debt settlement instructions using min-cash-flow minimization.
    Returns the minimum number of transactions needed for all members to settle up.
    """
    settlement = SettlementService.get_trip_settlement(db, trip_id)
    return ResponseEnvelope[TripSettlementResponse](
        data=settlement,
        message=f"Debt settlement plan calculated ({settlement.total_transactions} transactions required).",
    )
