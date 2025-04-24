from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from terminal_routes import router as terminal_router
from auth_routes import router as auth_router  # New

app = FastAPI(title="APG Universal Terminal Engine",
             description="Core brain for terminal applications")

# Enhanced CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Terminal-API-Version"] 
)

# API Versioning
@app.middleware("http")
async def add_version_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Terminal-API-Version"] = "2.0"
    return response

# Include all routers
app.include_router(auth_router, prefix="/auth")
app.include_router(terminal_router, prefix="/terminal")
