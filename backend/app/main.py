from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine, Base, ensure_schema_compatibility
# Import all models to ensure metadata registration
import app.models  # noqa: F401
from app.utils.file_storage import ensure_upload_dir

from app.api.routers.auth import router as auth_router
from app.api.routers.profile import router as profile_router
from app.api.routers.resumes import router as resumes_router
from app.api.routers.intelligence import router as intelligence_router
from app.api.routers.opportunities import router as opportunities_router
from app.api.routers.providers import router as providers_router
from app.api.routers.cosgo import router as cosgo_router
from app.api.routers.outreach import router as outreach_router
from app.api.routers.gmail import router as gmail_router
from app.api.routers.learning import router as learning_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure upload folder and database tables exist
    ensure_upload_dir()
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="OutReachIQ: Autonomous AI Career & Opportunity Agent - Research Prototype & Software Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers with API_V1 prefix
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(profile_router, prefix=settings.API_V1_STR)
app.include_router(resumes_router, prefix=settings.API_V1_STR)
app.include_router(intelligence_router, prefix=settings.API_V1_STR)
app.include_router(opportunities_router, prefix=settings.API_V1_STR)
app.include_router(providers_router, prefix=settings.API_V1_STR)
app.include_router(cosgo_router, prefix=settings.API_V1_STR)
app.include_router(outreach_router, prefix=settings.API_V1_STR)
app.include_router(gmail_router, prefix=settings.API_V1_STR)
app.include_router(learning_router, prefix=settings.API_V1_STR)

# Also expose without prefix for ease of testing / direct spec compliance
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(resumes_router)
app.include_router(intelligence_router)
app.include_router(opportunities_router)
app.include_router(providers_router)
app.include_router(cosgo_router)
app.include_router(outreach_router)
app.include_router(gmail_router)
app.include_router(learning_router)




@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "OutReachIQ Backend API"}
