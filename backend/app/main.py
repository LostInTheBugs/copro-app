import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import get_settings
from app.core.database import init_db
from app.routes import auth, copro, lots, comptes, ag, documents, carnet, export, email, relances, travaux, consolide, contacts, contrats

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    init_db()
    from app.core.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="CoproApp", version="2026.08.100", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev ; en prod le frontend est servi par le même backend
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, copro, lots, comptes, ag, documents, carnet, export, email, relances, travaux, consolide, contacts, contrats):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# Frontend statique (build Vite) servi par le backend en production,
# avec fallback SPA pour les routes profondes (refresh sur /ag, /comptes…)
if settings.frontend_dist and os.path.isdir(settings.frontend_dist):
    dist = settings.frontend_dist

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        base = os.path.abspath(dist)
        full = os.path.abspath(os.path.join(base, full_path))
        if os.path.isfile(full) and full.startswith(base):
            # Les fichiers Vite ont un hash de contenu dans leur nom → cache long.
            cache = "public, max-age=31536000, immutable" if full_path.startswith("assets/") else "no-cache"
            return FileResponse(full, headers={"Cache-Control": cache})
        index = os.path.join(base, "index.html")
        if os.path.isfile(index):
            # index.html jamais mis en cache : le navigateur récupère toujours le
            # dernier bundle (évite les boucles/bugs liés à un ancien JS).
            return FileResponse(index, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        raise HTTPException(404, "Not Found")
