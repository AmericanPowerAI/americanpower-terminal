from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from terminal_routes import router as terminal_router

app = FastAPI()

# CORS Middleware - update 'allow_origins' to your frontend domain for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with ["https://yourfrontend.com"] in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include terminal functionality routes under /terminal
app.include_router(terminal_router, prefix="/terminal")
