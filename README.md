# Travel Expense Tracker API

A production-grade REST API built with **FastAPI**, **MongoDB** (PyMongo), and **Pydantic v2** for managing group trips, tracking shared expenses, calculating category spending breakdowns, and computing optimal debt settlements.

---

## 🚀 Key Features

1. **Trip & Group Member Management**:
   - Create, list, inspect, update, and delete trips.
   - Enforce member uniqueness and date consistency (`start_date <= end_date`).
   - Add/remove members with safety checks (prevents deleting members with existing payments or split shares).
   - Cascading deletions of expenses when a trip is deleted.

2. **Expense Tracking with Exact Cent-Balanced Splits**:
   - Record expenses with categories, payer, and shared members.
   - **Exact Split Algorithm**: Distributes fractional remainder cents so the sum of individual shares strictly equals the total amount.
   - Membership validation: Enforces that payers and shared members belong to the trip.
   - Full filtering (category, payer, date range, amount range), sorting (date/amount, asc/desc), and pagination.

3. **Financial Analytics & Debt Settlement Minimization**:
   - **Summary Endpoint**: Provides total expenses, category spending breakdown (amount, count, percentage), and individual member balances (total paid, total share owed, net balance).
   - **Optimal Debt Settlement**: Implements a min-cash-flow greedy debt settlement algorithm that minimizes the total number of transactions needed to settle all debts in the group.

4. **Production Architecture**:
   - Standardized JSON envelopes for success (`ResponseEnvelope[T]`) and errors (`ErrorEnvelope`).
   - Clean exception hierarchy with proper HTTP status codes (400, 404, 422, 500, 503).
   - CORS middleware enabled.
   - Mock-ready test suite running without external daemon dependencies.

---

## 📁 Project Structure

```
expense-tracker/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── trips.py          # Trip CRUD and member endpoints
│   │       │   ├── expenses.py       # Expense CRUD, filtering & pagination
│   │       │   └── settlements.py    # Summary & optimal debt settlements
│   │       └── api.py                # Aggregated v1 API router
│   ├── core/
│   │   ├── config.py                 # Pydantic BaseSettings & env configs
│   │   ├── exceptions.py             # Domain and application exception classes
│   │   └── logging.py                # Formatted application logger
│   ├── database/
│   │   ├── connection.py             # PyMongo client lifecycle manager
│   │   └── indexes.py                # Automated index verification
│   ├── schemas/
│   │   ├── common.py                 # ResponseEnvelope, ErrorEnvelope, Pagination
│   │   ├── expense.py                # Expense request & response Pydantic models
│   │   ├── summary.py                # Financial summary & settlement models
│   │   └── trip.py                   # Trip & member request & response models
│   ├── services/
│   │   ├── expense_service.py        # Split math & expense business logic
│   │   ├── settlement_service.py     # Cash-flow minimization & analytics
│   │   └── trip_service.py           # Trip & member business logic
│   ├── utils/
│   │   └── object_id.py              # PyObjectId validator & BSON sanitizers
│   └── main.py                       # FastAPI application & exception handlers
├── tests/
│   ├── conftest.py                   # Mongomock fixture & TestClient setup
│   ├── test_trips.py                 # Trip CRUD & member validation tests
│   ├── test_expenses.py              # Exact split math & expense tests
│   ├── test_settlements.py           # Category analytics & settlement tests
│   └── test_advanced.py              # Multi-party settlements & edge cases
├── .env                              # Environment variables
├── .env.example                      # Example environment variables
└── requirements.txt                  # Python dependencies
```

---

## 🛠️ Getting Started

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Running Locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Running Tests

Run the test suite with `pytest`:

```bash
pytest -v
```

All tests execute with in-memory MongoDB mocking (`mongomock`), allowing instantaneous execution without needing a running MongoDB instance.

---

## 📡 API Reference Summary

### Trips (`/api/v1/trips`)
- `POST /api/v1/trips` - Create trip
- `GET /api/v1/trips` - List trips
- `GET /api/v1/trips/{trip_id}` - Get trip details
- `PUT /api/v1/trips/{trip_id}` - Update trip metadata
- `DELETE /api/v1/trips/{trip_id}` - Delete trip (cascades to expenses)
- `POST /api/v1/trips/{trip_id}/members` - Add member
- `DELETE /api/v1/trips/{trip_id}/members/{member_id}` - Remove member

### Expenses (`/api/v1/trips/{trip_id}/expenses`)
- `POST /api/v1/trips/{trip_id}/expenses` - Log expense with auto-calculated splits
- `GET /api/v1/trips/{trip_id}/expenses` - List expenses (with filters, sort, and pagination)
- `GET /api/v1/trips/{trip_id}/expenses/{expense_id}` - Get single expense
- `PUT /api/v1/trips/{trip_id}/expenses/{expense_id}` - Update expense
- `DELETE /api/v1/trips/{trip_id}/expenses/{expense_id}` - Delete expense

### Settlements & Summary (`/api/v1/trips/{trip_id}`)
- `GET /api/v1/trips/{trip_id}/summary` - Full financial breakdown & category stats
- `GET /api/v1/trips/{trip_id}/settlement` - Minimized payment transactions to settle all debts
