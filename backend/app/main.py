import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.core.database import init_db
from app.routes import auth, copro, lots, comptes, ag, documents, carnet, export

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    init_db()
    yield


app = FastAPI(title="CoproApp", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev ; en prod le frontend est servi par le même backend
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, copro, lots, comptes, ag, documents, carnet, export):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# Frontend statique (build Vite) servi par le backend en production
if settings.frontend_dist and os.path.isdir(settings.frontend_dist):
    dist = settings.frontend_dist
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
