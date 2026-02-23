"""
MedGemma Clinical Suite API
Main application entry point.

This is the FastAPI application that powers the MedGemma Clinical Suite,
providing endpoints for patient management, clinical data, imaging,
and AI-powered medical analysis.
"""

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.core.config import settings
from app.api.routes import api_router
from app.services.supabase_client import get_supabase_client
from app.services.ai_service import get_ai_service_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("=" * 50)
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 50)

    # Verify Supabase connection
    try:
        client = get_supabase_client()
        print("[OK] Supabase client initialized")
    except ValueError as e:
        print(f"[WARN] Supabase not configured: {e}")
    except Exception as e:
        print(f"[ERR] Supabase connection error: {e}")

    # Check AI service status
    ai_status = get_ai_service_status()
    mode = ai_status.get("mode", "unknown")
    if ai_status["configured"]:
        if mode == "debug":
            label = "Debug mode (no AI calls)"
        elif mode == "runpod":
            label = f"RunPod endpoint {ai_status.get('endpoint_id', '?')}"
        else:
            label = ai_status.get('api_url', mode)
        print(f"[OK] AI Service configured: {label}")
    else:
        print("[WARN] AI Service not configured (using mock responses)")

    print("=" * 50)
    print(f"API Documentation: http://localhost:8000{settings.API_V1_PREFIX}/docs")
    print("=" * 50)

    yield

    # Shutdown
    print("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## MedGemma Clinical Suite API

A comprehensive backend API for the MedGemma Clinical Suite, providing:

### Features
- **Patient Management**: Search, retrieve, and manage patient records
- **Clinical Data**: Vitals monitoring, clinical alerts, and notes
- **Imaging**: Medical image history and management
- **AI Analysis**: MedGemma-powered medical image analysis and consultations

### Authentication
All endpoints (except health check) require Bearer token authentication.
Use the `/auth/login` endpoint to obtain a token.

### Documentation
- **Swagger UI**: `/api/v1/docs`
- **ReDoc**: `/api/v1/redoc`
    """,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2)) + "ms"
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    if settings.DEBUG:
        # In debug mode, return detailed error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "path": str(request.url.path)
            }
        )
    else:
        # In production, return generic error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred"}
        )


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# =============================================================================
# Root Endpoints (outside /api/v1)
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    Returns basic API information.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the current health status of the API and its dependencies.
    """
    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "services": {}
    }

    # Check Supabase connection
    try:
        client = get_supabase_client()
        # Try a simple query to verify connection
        client.table("patients").select("id").limit(1).execute()
        health_status["services"]["database"] = {
            "status": "healthy",
            "type": "supabase"
        }
    except ValueError:
        health_status["services"]["database"] = {
            "status": "not_configured",
            "type": "supabase"
        }
        health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "type": "supabase",
            "error": str(e) if settings.DEBUG else "Connection failed"
        }
        health_status["status"] = "unhealthy"

    # Check AI service
    ai_status = get_ai_service_status()
    health_status["services"]["ai"] = {
        "status": "configured" if ai_status["configured"] else "mock_mode",
        "mode": ai_status["mode"]
    }

    return health_status


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Returns whether the API is ready to accept requests.
    """
    try:
        # Verify database connection
        client = get_supabase_client()
        client.table("patients").select("id").limit(1).execute()
        return {"ready": True}
    except:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ready": False, "reason": "Database not available"}
        )


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint.
    Returns whether the API process is alive.
    """
    return {"alive": True}


# =============================================================================
# Development/Debug Endpoints
# =============================================================================

if settings.DEBUG:

    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """
        Debug endpoint to view current configuration.
        Only available in DEBUG mode.
        """
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
            "cors_origins": settings.cors_origins_list,
            "supabase_configured": bool(settings.SUPABASE_URL),
            "ai_service_configured": bool(settings.MEDGEMMA_API_URL),
            "jwt_algorithm": settings.JWT_ALGORITHM,
            "token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        }

    @app.get("/debug/routes", tags=["Debug"])
    async def debug_routes():
        """
        Debug endpoint to list all registered routes.
        Only available in DEBUG mode.
        """
        routes = []
        for route in app.routes:
            if hasattr(route, "methods"):
                routes.append({
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": route.name
                })
        return {"routes": routes}


# =============================================================================
# Application Runner
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
