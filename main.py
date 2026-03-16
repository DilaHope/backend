"""
Point d'entrée FastAPI.
"""
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import scheduler as sched


@asynccontextmanager
async def lifespan(app: FastAPI):
    sched.start_scheduler()
    threading.Thread(target=sched.update_ranking, daemon=True).start()
    yield
    sched.scheduler.shutdown()


app = FastAPI(title="Crypto Gem Ranking API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/ranking")
def get_ranking(limit: int = Query(default=50, ge=1, le=100)):
    return {
        "last_update": sched.last_update,
        "count": len(sched.ranking_cache[:limit]),
        "top": sched.ranking_cache[:limit],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "cached_coins": len(sched.ranking_cache),
        "last_update": sched.last_update,
        "is_updating": sched.is_updating,
    }
