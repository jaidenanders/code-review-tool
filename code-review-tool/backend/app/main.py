import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.github import router as github_router
from app.api.routes.review import router as review_router
from app.db import init_db

_CORS_ORIGINS_DEFAULT = "http://localhost:5173,http://localhost:3000"
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _CORS_ORIGINS_DEFAULT).split(",")
    if o.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Code Review Tool API",
    description="AI-powered code review backed by Ollama and GitHub integration.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(github_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
