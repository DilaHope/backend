"""
Scheduler : pipeline de scoring avec publication progressive.
- Les coins sont ajoutés au cache AU FUR ET À MESURE (pas en fin de cycle)
- Le cache est sauvegardé dans cache.json pour survivre aux redémarrages / rate limits
"""

import time
import json
import os
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from config import REFRESH_INTERVAL_MINUTES, COINS_PAGES
from scoring import compute_score
from services.coingecko import get_small_cap_coins, get_coin_detail
from services.dexscreener import get_best_liquidity

CACHE_FILE = Path(__file__).parent / "cache.json"

# Cache global : dict indexé par coin id pour éviter les doublons
ranking_cache: list[dict] = []
last_update: str = ""
is_updating: bool = False

scheduler = BackgroundScheduler()


def _load_cache_from_disk() -> None:
    """Charge le cache depuis cache.json au démarrage."""
    global ranking_cache, last_update
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            ranking_cache = saved.get("top", [])
            last_update   = saved.get("last_update", "")
            print(f"[Cache] {len(ranking_cache)} coins chargés depuis le disque ({last_update})")
        except Exception as e:
            print(f"[Cache] Erreur lecture cache.json: {e}")


def _save_cache_to_disk() -> None:
    """Persiste le cache courant dans cache.json."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_update": last_update, "top": ranking_cache}, f, ensure_ascii=False)
    except Exception as e:
        print(f"[Cache] Erreur écriture cache.json: {e}")


def _upsert(coin: dict) -> None:
    """
    Ajoute ou met à jour un coin dans le cache global par son id.
    Retrie le cache par score décroissant après chaque insertion.
    """
    global ranking_cache
    ranking_cache = [c for c in ranking_cache if c["id"] != coin["id"]]
    ranking_cache.append(coin)
    ranking_cache = sorted(ranking_cache, key=lambda x: x["score"], reverse=True)[:100]


def update_ranking() -> None:
    """
    Pipeline complet avec publication progressive :
    chaque coin scoré est immédiatement disponible via /ranking.
    """
    global last_update, is_updating
    if is_updating:
        print("[Scheduler] Mise à jour déjà en cours, skip.")
        return

    is_updating = True
    print("[Scheduler] Début de la mise à jour...")

    try:
        raw_coins = get_small_cap_coins(pages=COINS_PAGES)
        print(f"[Scheduler] {len(raw_coins)} small caps à scorer")

        for i, coin in enumerate(raw_coins):
            coin_id = coin.get("id", "")
            symbol  = coin.get("symbol", "")
            mc      = coin.get("market_cap") or 1
            vol     = coin.get("total_volume") or 0
            fdv     = coin.get("fully_diluted_valuation") or mc * 2

            detail      = get_coin_detail(coin_id)
            dev_data    = detail.get("developer_data") or {}
            community   = detail.get("community_data") or {}
            platforms   = detail.get("platforms") or {}
            liquidity   = get_best_liquidity(symbol, platforms)

            score = compute_score(
                market_cap=mc,
                volume_24h=vol,
                fdv=fdv,
                liquidity_usd=liquidity,
                dev_data=dev_data,
                community_data=community,
            )

            entry = {
                "id":                coin_id,
                "name":              coin.get("name"),
                "symbol":            symbol.upper(),
                "price":             coin.get("current_price"),
                "market_cap":        round(mc, 0),
                "volume_24h":        round(vol, 0),
                "fdv":               round(fdv, 0),
                "liquidity_usd":     round(liquidity, 0),
                "score":             score,
                "twitter_followers": community.get("twitter_followers"),
                "github_stars":      dev_data.get("stars"),
                "image":             coin.get("image"),
            }

            # Publication immédiate dans le cache + sauvegarde disque
            _upsert(entry)
            last_update = time.strftime("%Y-%m-%d %H:%M:%S")
            _save_cache_to_disk()

            if (i + 1) % 10 == 0:
                print(f"[Scheduler] {i+1}/{len(raw_coins)} scorés — top score: {ranking_cache[0]['score'] if ranking_cache else 0}")

            time.sleep(1.5)

        last_update = time.strftime("%Y-%m-%d %H:%M:%S")
        _save_cache_to_disk()
        print(f"[Scheduler] ✅ Cycle terminé — {len(ranking_cache)} coins dans le cache — {last_update}")

    except Exception as e:
        print(f"[Scheduler] Erreur inattendue: {e}")
    finally:
        is_updating = False


def start_scheduler() -> None:
    _load_cache_from_disk()
    if not scheduler.running:
        scheduler.add_job(update_ranking, "interval", minutes=REFRESH_INTERVAL_MINUTES)
        scheduler.start()
        print(f"[Scheduler] Démarré — refresh toutes les {REFRESH_INTERVAL_MINUTES} min")
