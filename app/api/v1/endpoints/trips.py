from fastapi import APIRouter, Depends, Query, status
from pymongo.database import Database

from app.database.connection import get_db
from app.schemas.common import ResponseEnvelope
from app.schemas.trip import MemberCreate, TripCreate, TripResponse, TripUpdate
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("", response_model=ResponseEnvelope[TripResponse], status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_in: TripCreate,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[TripResponse]:
    """Create a new trip with an initial list of members."""
    trip = TripService.create_trip(db, trip_in)
    return ResponseEnvelope[TripResponse](
        data=trip,
        message=f"Trip '{trip.name}' created successfully.",
    )


@router.get("", response_model=ResponseEnvelope[list[TripResponse]])
async def list_trips(
    skip: int = Query(default=0, ge=0, description="Offset items"),
    limit: int = Query(default=50, ge=1, le=100, description="Max items per page"),
    db: Database = Depends(get_db),
) -> ResponseEnvelope[list[TripResponse]]:
    """Retrieve all trips ordered by most recently created."""
    trips = TripService.list_trips(db, skip=skip, limit=limit)
    return ResponseEnvelope[list[TripResponse]](
        data=trips,
        message=f"Retrieved {len(trips)} trips.",
    )


@router.get("/{trip_id}", response_model=ResponseEnvelope[TripResponse])
async def get_trip(
    trip_id: str,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[TripResponse]:
    """Get trip details by ObjectId."""
    trip = TripService.get_trip(db, trip_id)
    return ResponseEnvelope[TripResponse](
        data=trip,
        message="Trip retrieved successfully.",
    )


@router.put("/{trip_id}", response_model=ResponseEnvelope[TripResponse])
async def update_trip(
    trip_id: str,
    trip_in: TripUpdate,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[TripResponse]:
    """Update trip metadata (name, destination, dates)."""
    trip = TripService.update_trip(db, trip_id, trip_in)
    return ResponseEnvelope[TripResponse](
        data=trip,
        message="Trip updated successfully.",
    )


@router.delete("/{trip_id}", response_model=ResponseEnvelope[dict])
async def delete_trip(
    trip_id: str,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[dict]:
    """Delete a trip and cascade delete all its expenses."""
    TripService.delete_trip(db, trip_id)
    return ResponseEnvelope[dict](
        data={"trip_id": trip_id, "deleted": True},
        message="Trip and all associated expenses deleted successfully.",
    )


@router.post("/{trip_id}/members", response_model=ResponseEnvelope[TripResponse])
async def add_member(
    trip_id: str,
    member_in: MemberCreate,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[TripResponse]:
    """Add a new member to an existing trip."""
    trip = TripService.add_member(db, trip_id, member_in)
    return ResponseEnvelope[TripResponse](
        data=trip,
        message=f"Member '{member_in.name}' added to trip successfully.",
    )


@router.delete("/{trip_id}/members/{member_id}", response_model=ResponseEnvelope[TripResponse])
async def remove_member(
    trip_id: str,
    member_id: str,
    db: Database = Depends(get_db),
) -> ResponseEnvelope[TripResponse]:
    """Remove a member from a trip (permitted only if member has no associated expenses)."""
    trip = TripService.remove_member(db, trip_id, member_id)
    return ResponseEnvelope[TripResponse](
        data=trip,
        message="Member removed from trip successfully.",
    )
