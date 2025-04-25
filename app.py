from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import psutil
from contextlib import asynccontextmanager

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
    logger.info("Starting APG Terminal Engine...")
    yield
    # Shutdown
    logger.info("Shutting down...")

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

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Terminal Endpoints
@app.post("/terminal/execute")
async def execute_command(command: dict):
    """Core terminal execution endpoint"""
    try:
        result = {"output": f"Executed: {command.get('cmd')}"}
        return result
    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        raise HTTPException(500, "Command execution failed")

@app.get("/terminal/status")
async def terminal_status():
    return {"status": "active", "version": app.version}

# Health Check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": app.version}

# Error Handling
@app.exception_handler(Exception)
async def handle_exceptions(request: Request, exc: Exception):
    logger.error(f"Error processing {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Resource Monitoring
@app.middleware("http")
async def check_resources(request: Request, call_next):
    if psutil.cpu_percent() > 90:
        raise HTTPException(429, "Server under heavy load")
    return await call_next(request)
