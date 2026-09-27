from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger
from app.database.connection import db_manager
from app.database.indexes import create_db_indexes
from pymongo.errors import PyMongoError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle events."""
    logger.info("Initializing %s in [%s] environment...", settings.PROJECT_NAME, settings.APP_ENV)
    # Establish MongoDB connection
    db_manager.connect()

    if db_manager.ping():
        logger.info("MongoDB is reachable. Ensuring indexes...")
        try:
            create_db_indexes(db_manager.get_database())
        except Exception as exc:
            logger.warning("Could not initialize indexes: %s", exc)
    else:
        logger.warning("MongoDB ping failed on startup. Application started in degraded state.")

    yield

    # Clean shutdown
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    db_manager.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Production-grade REST API for travel expense tracking and debt settlement.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("Application exception [%s] on %s: %s", exc.code, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg"), "type": err.get("type")})

    logger.warning("Validation error on %s: %s", request.url.path, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed. Please check the provided fields.",
                "details": errors,
            },
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning("Value error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "BAD_REQUEST",
                "message": str(exc),
                "details": None,
            },
        },
    )


@app.exception_handler(PyMongoError)
async def mongo_exception_handler(request: Request, exc: PyMongoError) -> JSONResponse:
    logger.error("MongoDB database error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "Cannot connect to MongoDB. Please ensure the MongoDB server is running or check your MONGODB_URI in .env.",
                "details": {"uri": settings.MONGODB_URI, "reason": str(exc)},
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled server exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": None,
            },
        },
    )


# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "project": settings.PROJECT_NAME,
        "environment": settings.APP_ENV,
        "status": "online",
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX,
    }


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Health check endpoint validating application and MongoDB connectivity."""
    db_reachable = db_manager.ping()
    is_healthy = db_reachable

    payload = {
        "status": "healthy" if is_healthy else "degraded",
        "environment": settings.APP_ENV,
        "database": {
            "connected": db_reachable,
            "database_name": settings.DATABASE_NAME,
        },
    }

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)
