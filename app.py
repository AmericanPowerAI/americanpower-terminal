from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
import logging
import os
from contextlib import asynccontextmanager
from terminal_routes import router as terminal_router
from auth_routes import router as auth_router
from monitoring import setup_metrics  # Custom module you'll create

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Redis connection...")
    redis_client = redis.from_url(
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379",
        encoding="utf-8",
        decode_responses=True
    )
    FastAPICache.init(RedisBackend(redis_client), prefix="apg-cache")
    await FastAPILimiter.init(redis_client)
    
    # Initialize monitoring
    setup_metrics(app)
    
    yield
    
    # Shutdown
    logger.info("Closing connections...")
    await FastAPILimiter.close()
    await FastAPICache.clear()

app = FastAPI(
    title="APG Universal Terminal Engine",
    description="Core brain for terminal applications across all platforms",
    version="2.3.0",
    lifespan=lifespan,
    docs_url="/developer/docs",
    redoc_url="/developer/redoc",
    contact={
        "name": "APG DevOps",
        "email": "devops@americanpowerglobal.com"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://americanpowerglobal.com/terms"
    }
)

# =====================
# SECURITY MIDDLEWARE
# =====================
if os.getenv("ENV") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
    
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-API-Version", "X-RateLimit-Limit"]
)

# =====================
# ROUTES
# =====================
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(RateLimiter(times=5, minutes=1))]
)

app.include_router(
    terminal_router,
    prefix="/terminal",
    tags=["Terminal Engine"],
    dependencies=[Depends(RateLimiter(times=30, minutes=1))]
)

# =====================
# MONITORING ENDPOINTS
# =====================
@app.get("/health", include_in_schema=False)
@cache(expire=10)
async def health_check():
    return {
        "status": "healthy",
        "version": app.version,
        "redis": "connected" if FastAPICache.get_backend() else "disconnected"
    }

@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

# =====================
# STATIC FILES (For web clients)
# =====================
app.mount("/static", StaticFiles(directory="static"), name="static")

# =====================
# ERROR HANDLERS
# =====================
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    logger.error(f"HTTP Error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "documentation": request.url_for("developer_docs")
        }
    )

@app.exception_handler(Exception)
async def universal_exception_handler(request, exc):
    logger.critical(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request.state.request_id
        }
    )

# =====================
# WEBHOOK EXAMPLE
# =====================
@app.post("/webhooks/command-log", include_in_schema=False)
async def log_command_webhook(payload: dict):
    """For external systems to receive command logs"""
    logger.info(f"Webhook received: {payload}")
    return {"status": "logged"}

# GPU acceleration
app.state.llm_engine = load_ai_model("gpt-4-turbo", device="cuda")

# Real-time monitoring
@app.middleware("http")
async def resource_monitor(request: Request, call_next):
    if psutil.cpu_percent() > 90:
        raise HTTPException(429, "Server overloaded")
    return await call_next(request)
