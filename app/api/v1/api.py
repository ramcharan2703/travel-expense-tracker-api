from fastapi import APIRouter

from app.api.v1.endpoints import expenses, settlements, trips

api_router = APIRouter()
api_router.include_router(trips.router)
api_router.include_router(expenses.router)
api_router.include_router(settlements.router)
