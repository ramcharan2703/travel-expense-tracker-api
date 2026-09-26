from decimal import Decimal
from typing import Generator
import mongomock
import mongomock.filtering
import pytest
from bson.decimal128 import Decimal128
from starlette.testclient import TestClient

from app.database.connection import db_manager, get_db
from app.main import app

# Teach mongomock how to compare and sort BSON Decimal128 objects
orig_get_compare_type = mongomock.filtering._get_compare_type
mongomock.filtering._get_compare_type = (
    lambda val: 1 if isinstance(val, Decimal128) else orig_get_compare_type(val)
)

Decimal128.__lt__ = lambda self, other: self.to_decimal() < (
    other.to_decimal() if isinstance(other, Decimal128) else Decimal(str(other))
)
Decimal128.__le__ = lambda self, other: self.to_decimal() <= (
    other.to_decimal() if isinstance(other, Decimal128) else Decimal(str(other))
)
Decimal128.__gt__ = lambda self, other: self.to_decimal() > (
    other.to_decimal() if isinstance(other, Decimal128) else Decimal(str(other))
)
Decimal128.__ge__ = lambda self, other: self.to_decimal() >= (
    other.to_decimal() if isinstance(other, Decimal128) else Decimal(str(other))
)


@pytest.fixture
def mock_db(monkeypatch: pytest.MonkeyPatch) -> Generator[mongomock.database.Database, None, None]:
    client = mongomock.MongoClient()
    db = client.get_database("test_db")

    # Patch db_manager methods to bypass live MongoDB connection timeouts
    monkeypatch.setattr(db_manager, "connect", lambda: None)
    monkeypatch.setattr(db_manager, "close", lambda: None)
    monkeypatch.setattr(db_manager, "ping", lambda: True)
    monkeypatch.setattr(db_manager, "get_database", lambda: db)
    db_manager.db = db

    yield db
    client.close()


@pytest.fixture
def client(mock_db: mongomock.database.Database) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
