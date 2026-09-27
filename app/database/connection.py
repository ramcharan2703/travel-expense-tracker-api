import re
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, PyMongoError, ServerSelectionTimeoutError

from app.core.config import settings
from app.core.logging import logger


def _mask_uri(uri: str) -> str:
    """Masks credentials in MongoDB connection URI for safe logging."""
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)


class DatabaseManager:
    """Manages the lifecycle of MongoDB connection and client pool."""

    def __init__(self) -> None:
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def connect(self) -> None:
        """Establishes connection to MongoDB using configured URI."""
        try:
            logger.info("Connecting to MongoDB at %s...", _mask_uri(settings.MONGODB_URI))
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=10,
            )
            self.db = self.client[settings.DATABASE_NAME]
            # Quick ping to verify connectivity
            self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB database: [%s]", settings.DATABASE_NAME)
        except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
            logger.warning(
                "MongoDB is currently unreachable at %s: %s. The app will run, but database operations will fail until MongoDB is started.",
                _mask_uri(settings.MONGODB_URI),
                exc,
            )
        except PyMongoError as exc:
            logger.error("Unexpected PyMongo error during connection initialization: %s", exc)

    def close(self) -> None:
        """Closes the MongoDB client connection pool."""
        if self.client:
            logger.info("Closing MongoDB connection...")
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed.")

    def get_database(self) -> Database:
        """Returns the active MongoDB database instance."""
        if self.db is None:
            # Attempt re-connection if client was not connected
            self.connect()
        if self.db is None:
            raise ConnectionFailure(
                "Cannot connect to MongoDB. Ensure MongoDB is running and the database configuration is correct."
            )
        return self.db

    def ping(self) -> bool:
        """Pings the MongoDB server to verify live status."""
        if self.client is None:
            return False
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False


db_manager = DatabaseManager()


def get_db() -> Database:
    """FastAPI dependency yielding the MongoDB database instance."""
    return db_manager.get_database()
