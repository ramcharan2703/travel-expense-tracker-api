from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import PyMongoError
from app.core.logging import logger


def create_db_indexes(db: Database) -> None:
    """Creates required indexes on MongoDB collections idempotently."""
    try:
        # Indexes for 'trips' collection
        logger.info("Configuring indexes for 'trips' collection...")
        db.trips.create_index([("created_at", DESCENDING)], name="idx_trips_created_at_desc")

        # Indexes for 'expenses' collection
        logger.info("Configuring indexes for 'expenses' collection...")
        db.expenses.create_index(
            [("trip_id", ASCENDING), ("date", DESCENDING)],
            name="idx_expenses_trip_date",
        )
        db.expenses.create_index(
            [("trip_id", ASCENDING), ("category", ASCENDING)],
            name="idx_expenses_trip_category",
        )
        db.expenses.create_index(
            [("trip_id", ASCENDING), ("paid_by", ASCENDING)],
            name="idx_expenses_trip_paid_by",
        )
        db.expenses.create_index(
            [("trip_id", ASCENDING), ("amount", ASCENDING)],
            name="idx_expenses_trip_amount",
        )

        logger.info("All database indexes verified successfully.")
    except PyMongoError as exc:
        logger.error("Failed to configure database indexes: %s", exc)
