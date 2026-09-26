from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
import math
from typing import Any, Optional
from bson.decimal128 import Decimal128
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.core.exceptions import (
    BusinessRuleException,
    ExpenseNotFoundError,
    InvalidMemberError,
    TripNotFoundError,
)
from app.schemas.common import PaginatedResponse, PaginationMetadata
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseFilterParams,
    ExpenseResponse,
    ExpenseUpdate,
    SplitShare,
)
from app.services.trip_service import TripService
from app.utils.object_id import clean_mongo_doc, to_object_id


class ExpenseService:
    @staticmethod
    def calculate_splits(amount: Decimal, shared_by: list[str]) -> list[dict[str, Any]]:
        """
        Splits an expense amount equally among shared_by members.
        Any fractional cents remainder is distributed cent-by-cent to ensure
        the exact sum of individual shares equals the total amount.
        """
        if not shared_by:
            raise BusinessRuleException("shared_by must contain at least one member.")

        count = len(shared_by)
        base_share = (amount / Decimal(count)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        remainder = amount - (base_share * Decimal(count))
        remainder_cents = int((remainder * Decimal("100")).to_integral_value())

        splits: list[dict[str, Any]] = []
        for i, member_id in enumerate(shared_by):
            extra = Decimal("0.01") if i < remainder_cents else Decimal("0.00")
            share = base_share + extra
            splits.append(
                {
                    "member_id": member_id,
                    "share": Decimal128(str(share)),
                }
            )
        return splits

    @classmethod
    def validate_members(
        cls, trip: dict, paid_by: Optional[str] = None, shared_by: Optional[list[str]] = None
    ) -> None:
        """Validates that payer and shared members are registered in the trip."""
        valid_member_ids = {m["id"] for m in trip.get("members", [])}

        if paid_by is not None and paid_by not in valid_member_ids:
            raise InvalidMemberError(
                f"Payer ID '{paid_by}' is not a registered member of this trip.",
                invalid_members=[paid_by],
            )

        if shared_by is not None:
            invalid_ids = [m for m in shared_by if m not in valid_member_ids]
            if invalid_ids:
                raise InvalidMemberError(
                    f"The following shared member IDs are not registered in this trip: {invalid_ids}",
                    invalid_members=invalid_ids,
                )

    @classmethod
    def create_expense(cls, db: Database, trip_id: str, expense_in: ExpenseCreate) -> ExpenseResponse:
        trip = TripService.get_trip_doc(db, trip_id)
        trip_oid = to_object_id(trip_id)

        cls.validate_members(trip, paid_by=expense_in.paid_by, shared_by=expense_in.shared_by)

        splits = cls.calculate_splits(expense_in.amount, expense_in.shared_by)
        now = datetime.now(timezone.utc)
        expense_date = expense_in.date or now

        doc = {
            "trip_id": trip_oid,
            "title": expense_in.title,
            "amount": Decimal128(str(expense_in.amount)),
            "category": expense_in.category,
            "paid_by": expense_in.paid_by,
            "shared_by": expense_in.shared_by,
            "split_shares": splits,
            "date": expense_date,
            "description": expense_in.description,
            "created_at": now,
            "updated_at": now,
        }

        result = db.expenses.insert_one(doc)
        doc["_id"] = result.inserted_id

        # Update parent trip updated_at
        db.trips.update_one({"_id": trip_oid}, {"$set": {"updated_at": now}})

        return ExpenseResponse.model_validate(clean_mongo_doc(doc))

    @classmethod
    def get_expense_doc(cls, db: Database, trip_id: str, expense_id: str) -> dict:
        trip_oid = to_object_id(trip_id)
        expense_oid = to_object_id(expense_id)

        doc = db.expenses.find_one({"_id": expense_oid, "trip_id": trip_oid})
        if not doc:
            raise ExpenseNotFoundError(expense_id)
        return doc

    @classmethod
    def get_expense(cls, db: Database, trip_id: str, expense_id: str) -> ExpenseResponse:
        doc = cls.get_expense_doc(db, trip_id, expense_id)
        return ExpenseResponse.model_validate(clean_mongo_doc(doc))

    @classmethod
    def list_expenses(
        cls, db: Database, trip_id: str, params: ExpenseFilterParams
    ) -> PaginatedResponse[ExpenseResponse]:
        # Validate trip exists
        TripService.get_trip_doc(db, trip_id)
        trip_oid = to_object_id(trip_id)

        query: dict[str, Any] = {"trip_id": trip_oid}

        if params.category:
            query["category"] = {"$regex": f"^{params.category.strip()}$", "$options": "i"}

        if params.paid_by:
            query["paid_by"] = params.paid_by.strip()

        date_filter: dict[str, Any] = {}
        if params.date_from:
            date_filter["$gte"] = params.date_from
        if params.date_to:
            date_filter["$lte"] = params.date_to
        if date_filter:
            query["date"] = date_filter

        amount_filter: dict[str, Any] = {}
        if params.min_amount is not None:
            amount_filter["$gte"] = Decimal128(str(params.min_amount))
        if params.max_amount is not None:
            amount_filter["$lte"] = Decimal128(str(params.max_amount))
        if amount_filter:
            query["amount"] = amount_filter

        total_count = db.expenses.count_documents(query)

        sort_field = params.sort_by if params.sort_by in ("date", "amount") else "date"
        sort_direction = ASCENDING if params.sort_order == "asc" else DESCENDING

        skip = (params.page - 1) * params.limit
        cursor = db.expenses.find(query).sort(sort_field, sort_direction).skip(skip).limit(params.limit)

        items = [ExpenseResponse.model_validate(clean_mongo_doc(doc)) for doc in cursor]
        pages = math.ceil(total_count / params.limit) if total_count > 0 else 0

        return PaginatedResponse[ExpenseResponse](
            items=items,
            pagination=PaginationMetadata(
                page=params.page,
                limit=params.limit,
                total=total_count,
                pages=pages,
            ),
        )

    @classmethod
    def update_expense(
        cls, db: Database, trip_id: str, expense_id: str, expense_in: ExpenseUpdate
    ) -> ExpenseResponse:
        trip = TripService.get_trip_doc(db, trip_id)
        existing = cls.get_expense_doc(db, trip_id, expense_id)
        expense_oid = to_object_id(expense_id)
        trip_oid = to_object_id(trip_id)

        update_dict = expense_in.model_dump(exclude_unset=True)
        if not update_dict:
            return ExpenseResponse.model_validate(clean_mongo_doc(existing))

        # Check payer and sharers if updated
        paid_by = update_dict.get("paid_by", existing["paid_by"])
        shared_by = update_dict.get("shared_by", existing["shared_by"])
        cls.validate_members(trip, paid_by=paid_by, shared_by=shared_by)

        # If amount or shared_by changed, recalculate split shares
        amount = update_dict.get("amount")
        if amount is not None or "shared_by" in update_dict:
            effective_amount = (
                amount
                if amount is not None
                else existing["amount"].to_decimal()
                if hasattr(existing["amount"], "to_decimal")
                else Decimal(str(existing["amount"]))
            )
            splits = cls.calculate_splits(effective_amount, shared_by)
            update_dict["split_shares"] = splits

        if "amount" in update_dict:
            update_dict["amount"] = Decimal128(str(update_dict["amount"]))

        now = datetime.now(timezone.utc)
        update_dict["updated_at"] = now

        db.expenses.update_one({"_id": expense_oid, "trip_id": trip_oid}, {"$set": update_dict})
        db.trips.update_one({"_id": trip_oid}, {"$set": {"updated_at": now}})

        updated = cls.get_expense_doc(db, trip_id, expense_id)
        return ExpenseResponse.model_validate(clean_mongo_doc(updated))

    @classmethod
    def delete_expense(cls, db: Database, trip_id: str, expense_id: str) -> bool:
        cls.get_expense_doc(db, trip_id, expense_id)
        expense_oid = to_object_id(expense_id)
        trip_oid = to_object_id(trip_id)

        result = db.expenses.delete_one({"_id": expense_oid, "trip_id": trip_oid})
        if result.deleted_count > 0:
            db.trips.update_one({"_id": trip_oid}, {"$set": {"updated_at": datetime.now(timezone.utc)}})
            return True
        return False
