"""
Point d'entrée FastAPI.
"""
import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import scheduler as sched

ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev
    "https://your-frontend.vercel.app",  # Vercel
    "https://frontend-yp86.onrender.com",  # Render
    "*"
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    sched.start_scheduler()
    threading.Thread(target=sched.update_ranking, daemon=True).start()
    yield
    sched.scheduler.shutdown()


app = FastAPI(title="Crypto Gem Ranking API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/ranking")
def get_ranking(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    data = sched.ranking_cache[offset:offset + limit]
    return {
        "last_update": sched.last_update,
        "count": len(sched.ranking_cache),
        "top": data,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "cached_coins": len(sched.ranking_cache),
        "last_update": sched.last_update,
        "is_updating": sched.is_updating,
    }
