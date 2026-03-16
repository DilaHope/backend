"""
Point d'entrée FastAPI.
Lance le scheduler au démarrage et expose les endpoints.
"""

import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import scheduler as sched


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Charge le cache disque EN PREMIER pour que /ranking réponde immédiatement
    sched.start_scheduler()
    # Puis lance la mise à jour en arrière-plan (non-bloquant)
    threading.Thread(target=sched.update_ranking, daemon=True).start()
    yield
    # Arrêt propre
    sched.scheduler.shutdown()


app = FastAPI(
    title="Crypto Gem Ranking API",
    description="Classement des cryptos small cap par score de potentiel (low cap + momentum + communauté + dev).",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS : autorise le frontend React (localhost:5173 par défaut Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/ranking", summary="Classement des gems par score décroissant")
def get_ranking(limit: int = Query(default=50, ge=1, le=100)):
    """
    Retourne les `limit` meilleures cryptos triées par score décroissant.
    - score : 0–100 (plus c'est haut, plus le potentiel estimé est élevé)
    - Mise à jour toutes les 15 minutes en arrière-plan
    """
    return {
        "last_update": sched.last_update,
        "count": len(sched.ranking_cache[:limit]),
        "top": sched.ranking_cache[:limit],
    }


@app.get("/health", summary="Santé du service")
def health():
    return {
        "status": "ok",
        "cached_coins": len(sched.ranking_cache),
        "last_update": sched.last_update,
    }
