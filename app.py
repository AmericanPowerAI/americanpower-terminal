from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import logging
from logging.handlers import RotatingFileHandler  # Updated import
import os
import psutil
from contextlib import asynccontextmanager
import httpx
from typing import Annotated

# ===== Configuration =====
MAX_MEMORY = 450  # MB (Render free tier has 512MB)
MAX_REQUESTS = 8   # Conservative concurrency limit
API_KEY_NAME = "X-API-Key"

# ===== Security Setup =====
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def validate_api_key(api_key: str = Depends(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(403, "Invalid API key")
    return api_key

# ===== Enhanced Logging =====
class SecurityFilter(logging.Filter):
    def filter(self, record):
        # Redact sensitive information from logs
        if hasattr(record, 'msg'):
            record.msg = str(record.msg).replace(os.getenv("API_KEY", ""), "[REDACTED]")
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("api.log", maxBytes=1_000_000, backupCount=1),  # Fixed: Using RotatingFileHandler
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("APGEngine")
logger.addFilter(SecurityFilter())

# ===== State Management =====
class ServerState:
    def __init__(self):
        self.active_requests = 0
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=2)
        )

state = ServerState()

# ===== Lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting APG Terminal Engine - Render Free Tier Optimized")
    logger.info(f"Memory Limit: {MAX_MEMORY}MB | Concurrency: {MAX_REQUESTS}")
    
    yield
    
    # Shutdown
    await state.client.aclose()
    logger.info("Clean shutdown completed")

# ===== App Initialization =====
app = FastAPI(
    title="APG Universal Terminal Engine",
    description="Optimized for Render Free Tier with Enhanced Security",
    version="2.3.2",
    lifespan=lifespan,
    docs_url="/developer/docs" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None,
    redoc_url=None,
    contact={
        "name": "APG Security Team",
        "email": "security@americanpowerglobal.com"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://americanpowerglobal.com/terms"
    }
)

# ===== Middleware =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["POST"],  # Only POST for terminal/execute
    allow_headers=[API_KEY_NAME, "Content-Type"],
    max_age=300  # Reduced from 600
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # Increased from 500
)

# ===== Rate Limiting =====
@app.middleware("http")
async def resource_limiter(request: Request, call_next):
    # Memory check
    mem = psutil.virtual_memory()
    used_mb = mem.used / (1024 ** 2)
    if used_mb > MAX_MEMORY:
        logger.warning(f"Memory threshold exceeded: {used_mb:.1f}MB")
        raise HTTPException(429, detail={
            "error": "System busy",
            "status": "retry_after_30s"
        })
    
    # Concurrency check
    if state.active_requests >= MAX_REQUESTS:
        logger.warning(f"Concurrent limit reached: {state.active_requests}")
        raise HTTPException(429, detail={
            "error": "Too many requests",
            "status": "retry_after_15s"
        })
    
    state.active_requests += 1
    try:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
    finally:
        state.active_requests -= 1

# ===== Endpoints =====
@app.post("/terminal/execute")
async def execute_command(
    request: Request,
    api_key: Annotated[str, Depends(validate_api_key)]
):
    """Secure command execution endpoint"""
    try:
        # Validate content type
        if request.headers.get("content-type") != "application/json":
            raise HTTPException(415, "Unsupported Media Type")
            
        command = await request.json()
        
        # Basic input validation
        if not command.get("cmd"):
            raise HTTPException(422, "Missing command")
            
        if len(command["cmd"]) > 200:
            raise HTTPException(413, "Command too long")
        
        # Add your actual command execution logic here
        return {
            "status": "success",
            "output": f"Processed: {command['cmd'][:50]}...",  # Truncated for security
            "resource_usage": f"{psutil.cpu_percent()}% CPU"
        }
        
    except ValueError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        raise HTTPException(400, "Invalid JSON")
    except Exception as e:
        logger.error(f"Execution error: {str(e)}", exc_info=True)
        raise HTTPException(500, "Command processing failed")

@app.get("/health")
async def health_check():
    """Lightweight health check"""
    try:
        mem = psutil.virtual_memory()
        return {
            "status": "operational",
            "version": app.version,
            "resources": {
                "memory": f"{mem.used / (1024 ** 2):.1f}/{mem.total / (1024 ** 2):.1f} MB",
                "cpu": f"{psutil.cpu_percent()}%",
                "active_requests": state.active_requests
            },
            "limits": {
                "max_memory": f"{MAX_MEMORY}MB",
                "max_concurrency": MAX_REQUESTS
            }
        }
    except Exception as e:
        logger.critical(f"Health check failed: {str(e)}")
        raise HTTPException(500, "Health check unavailable")

# ===== Error Handling =====
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        f"HTTP Error {exc.status_code} at {request.url}: {exc.detail}",
        extra={"client": request.client.host}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers={"Cache-Control": "no-store"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.critical(
        f"Unexpected error at {request.url}",
        exc_info=True,
        extra={"client": request.client.host}
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal system error"},
        headers={
            "Cache-Control": "no-store",
            "Retry-After": "30"
        }
    )
