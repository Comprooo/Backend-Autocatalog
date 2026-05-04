from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import init_db, close_db
from app.routes.v1 import auth, cars, admin_cars, schedules, admin_schedules, admin_stats, upload, ai

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc), "data": None}
    )

app.include_router(auth.router, prefix="/api/v1")
app.include_router(cars.router, prefix="/api/v1")
app.include_router(admin_cars.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(admin_schedules.router, prefix="/api/v1")
app.include_router(admin_stats.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/version", tags=["system"])
async def get_version():
    return {"version": "1.0.0"}

@app.get("/chat", include_in_schema=False)
async def chat_ui():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return FileResponse(os.path.join(static_dir, "chat.html"))
