import uuid
from datetime import datetime, timezone
from typing import Optional
from pymongo.database import Database

from app.core.exceptions import (
    BusinessRuleException,
    MemberNotFoundError,
    TripNotFoundError,
)
from app.schemas.trip import MemberCreate, TripCreate, TripResponse, TripUpdate
from app.utils.object_id import clean_mongo_doc, to_object_id


class TripService:
    @staticmethod
    def create_trip(db: Database, trip_in: TripCreate) -> TripResponse:
        now = datetime.now(timezone.utc)
        members_data = []
        for m in trip_in.members:
            members_data.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "name": m.name,
                    "email": m.email,
                    "joined_at": now,
                }
            )

        doc = {
            "name": trip_in.name,
            "destination": trip_in.destination,
            "start_date": trip_in.start_date.isoformat(),
            "end_date": trip_in.end_date.isoformat(),
            "members": members_data,
            "created_at": now,
            "updated_at": now,
        }

        result = db.trips.insert_one(doc)
        doc["_id"] = result.inserted_id
        return TripResponse.model_validate(clean_mongo_doc(doc))

    @staticmethod
    def list_trips(db: Database, skip: int = 0, limit: int = 50) -> list[TripResponse]:
        cursor = db.trips.find().sort("created_at", -1).skip(skip).limit(limit)
        trips = []
        for doc in cursor:
            trips.append(TripResponse.model_validate(clean_mongo_doc(doc)))
        return trips

    @staticmethod
    def get_trip_doc(db: Database, trip_id: str) -> dict:
        oid = to_object_id(trip_id)
        doc = db.trips.find_one({"_id": oid})
        if not doc:
            raise TripNotFoundError(trip_id)
        return doc

    @classmethod
    def get_trip(cls, db: Database, trip_id: str) -> TripResponse:
        doc = cls.get_trip_doc(db, trip_id)
        return TripResponse.model_validate(clean_mongo_doc(doc))

    @classmethod
    def update_trip(cls, db: Database, trip_id: str, trip_in: TripUpdate) -> TripResponse:
        oid = to_object_id(trip_id)
        trip = cls.get_trip_doc(db, trip_id)

        update_data = trip_in.model_dump(exclude_unset=True)
        if "start_date" in update_data and update_data["start_date"] is not None:
            update_data["start_date"] = update_data["start_date"].isoformat()
        if "end_date" in update_data and update_data["end_date"] is not None:
            update_data["end_date"] = update_data["end_date"].isoformat()

        # Date consistency check against existing trip if only one date is updated
        start = update_data.get("start_date", trip["start_date"])
        end = update_data.get("end_date", trip["end_date"])
        if str(end) < str(start):
            raise BusinessRuleException("end_date cannot be earlier than start_date.")

        if update_data:
            update_data["updated_at"] = datetime.now(timezone.utc)
            db.trips.update_one({"_id": oid}, {"$set": update_data})

        updated_doc = cls.get_trip_doc(db, trip_id)
        return TripResponse.model_validate(clean_mongo_doc(updated_doc))

    @classmethod
    def delete_trip(cls, db: Database, trip_id: str) -> bool:
        oid = to_object_id(trip_id)
        # Check existence
        cls.get_trip_doc(db, trip_id)
        # Cascade delete associated expenses
        db.expenses.delete_many({"trip_id": oid})
        # Delete trip
        result = db.trips.delete_one({"_id": oid})
        return result.deleted_count > 0

    @classmethod
    def add_member(cls, db: Database, trip_id: str, member_in: MemberCreate) -> TripResponse:
        oid = to_object_id(trip_id)
        trip = cls.get_trip_doc(db, trip_id)

        existing_names = [m["name"].strip().lower() for m in trip.get("members", [])]
        if member_in.name.strip().lower() in existing_names:
            raise BusinessRuleException(f"Member with name '{member_in.name}' already exists in this trip.")

        now = datetime.now(timezone.utc)
        new_member = {
            "id": uuid.uuid4().hex[:8],
            "name": member_in.name,
            "email": member_in.email,
            "joined_at": now,
        }

        db.trips.update_one(
            {"_id": oid},
            {
                "$push": {"members": new_member},
                "$set": {"updated_at": now},
            },
        )

        updated_doc = cls.get_trip_doc(db, trip_id)
        return TripResponse.model_validate(clean_mongo_doc(updated_doc))

    @classmethod
    def remove_member(cls, db: Database, trip_id: str, member_id: str) -> TripResponse:
        oid = to_object_id(trip_id)
        trip = cls.get_trip_doc(db, trip_id)

        members = trip.get("members", [])
        target_member = next((m for m in members if m["id"] == member_id), None)
        if not target_member:
            raise MemberNotFoundError(member_id)

        if len(members) <= 1:
            raise BusinessRuleException("Cannot remove the only member from a trip.")

        # Check if member has expenses or shared splits
        expense_as_payer = db.expenses.find_one({"trip_id": oid, "paid_by": member_id})
        if expense_as_payer:
            raise BusinessRuleException(
                f"Cannot remove member '{target_member['name']}' because they are the payer of recorded expenses."
            )

        expense_as_sharer = db.expenses.find_one({"trip_id": oid, "shared_by": member_id})
        if expense_as_sharer:
            raise BusinessRuleException(
                f"Cannot remove member '{target_member['name']}' because they share recorded expenses."
            )

        now = datetime.now(timezone.utc)
        db.trips.update_one(
            {"_id": oid},
            {
                "$pull": {"members": {"id": member_id}},
                "$set": {"updated_at": now},
            },
        )

        updated_doc = cls.get_trip_doc(db, trip_id)
        return TripResponse.model_validate(clean_mongo_doc(updated_doc))
