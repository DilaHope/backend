"""
Scheduler : pipeline de scoring avec publication progressive.
Cache JSON persistant sur disque.
"""
import time
import json
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

from config import REFRESH_INTERVAL_MINUTES, COINS_PAGES
from filters import is_valid
from scoring import compute_score
from services.coingecko import get_small_cap_coins, get_coin_detail
from services.dexscreener import get_dex_data
from services.defillama import get_tvl_for_symbol

CACHE_FILE = Path(__file__).parent / "cache.json"

ranking_cache: list[dict] = []
last_update: str = ""
is_updating: bool = False

scheduler = BackgroundScheduler()


def _load_cache_from_disk() -> None:
    global ranking_cache, last_update
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            ranking_cache = saved.get("top", [])
            last_update   = saved.get("last_update", "")
            print(f"[Cache] {len(ranking_cache)} coins chargés ({last_update})")
        except Exception as e:
            print(f"[Cache] Erreur lecture: {e}")


def _save_cache_to_disk() -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_update": last_update, "top": ranking_cache}, f, ensure_ascii=False)
    except Exception as e:
        print(f"[Cache] Erreur écriture: {e}")


def _upsert(coin: dict) -> None:
    global ranking_cache
    ranking_cache = [c for c in ranking_cache if c["id"] != coin["id"]]
    ranking_cache.append(coin)
    ranking_cache = sorted(ranking_cache, key=lambda x: x["score"], reverse=True)[:100]


def update_ranking() -> None:
    global last_update, is_updating
    if is_updating:
        print("[Scheduler] Mise à jour déjà en cours, skip.")
        return

    is_updating = True
    print("[Scheduler] Début de la mise à jour...")

    try:
        raw_coins = get_small_cap_coins(pages=COINS_PAGES)
        print(f"[Scheduler] {len(raw_coins)} small caps récupérés")

        for i, raw in enumerate(raw_coins):
            coin_id = raw.get("id", "")
            symbol  = raw.get("symbol", "")
            mc      = raw.get("market_cap") or 1
            vol     = raw.get("total_volume") or 0

            # Détail CoinGecko (dev, community, platforms, categories, description)
            detail     = get_coin_detail(coin_id)
            dev_data   = detail.get("developer_data") or {}
            community  = detail.get("community_data") or {}
            platforms  = detail.get("platforms") or {}
            categories = detail.get("categories") or []
            description = (detail.get("description") or {}).get("en") or ""

            # DexScreener (liquidité, volume DEX, age paire)
            dex = get_dex_data(symbol, platforms)

            # DefiLlama TVL (bonus pour projets DeFi)
            tvl = get_tvl_for_symbol(symbol)

            # Construire le coin enrichi pour le scoring
            coin = {
                "id":            coin_id,
                "name":          raw.get("name"),
                "symbol":        symbol.upper(),
                "price":         raw.get("current_price"),
                "market_cap":    mc,
                "volume_24h":    vol,
                "fdv":           raw.get("fully_diluted_valuation") or mc * 2,
                "liquidity":     dex["liquidity"],
                "dex_volume_24h": dex["dex_volume_24h"],
                "pair_age_days": dex["pair_age_days"],
                "tvl":           tvl,
                "dev_data":      dev_data,
                "community_data": community,
                "categories":    categories,
                "description":   description,
                # Holders / whales : non disponibles sans API on-chain payante
                # → valeurs neutres (pas de pénalité injuste)
                "holders_today":      0,
                "holders_week":       0,
                "top10_wallets_pct":  0,
                "whale_buy_volume":   0,
                "whale_sell_volume":  0,
                "image":         raw.get("image"),
            }

            # Filtre qualité
            if not is_valid(coin):
                continue

            score = compute_score(coin)
            sub   = coin.pop("_scores", {})

            entry = {
                "id":                          coin_id,
                "name":                        coin["name"],
                "symbol":                      coin["symbol"],
                "price":                       coin["price"],
                "market_cap":                  round(mc, 0),
                "volume_24h":                  round(vol, 0),
                "liquidity":                   round(dex["liquidity"], 0),
                "dex_volume_24h":              round(dex["dex_volume_24h"], 0),
                "pair_age_days":               round(dex["pair_age_days"], 1),
                "tvl":                         round(tvl, 0),
                "twitter_followers":           community.get("twitter_followers"),
                "github_commits_month":        dev_data.get("commit_count_4_weeks"),
                "github_stars":                dev_data.get("stars"),
                "dominant_narrative":          sub.get("dominant_narrative"),
                "narrative_score":             sub.get("narrative_score"),
                "whale_activity_score":        sub.get("whale_activity_score"),
                "cex_listing_potential_score": sub.get("cex_listing_potential_score"),
                "manipulation_score":          sub.get("manipulation_score"),
                "score":                       score,
                "image":                       coin["image"],
            }

            _upsert(entry)
            last_update = time.strftime("%Y-%m-%d %H:%M:%S")
            _save_cache_to_disk()

            if (i + 1) % 10 == 0:
                top = ranking_cache[0]["score"] if ranking_cache else 0
                print(f"[Scheduler] {i+1}/{len(raw_coins)} scorés — top: {top}")

            time.sleep(1.5)

        print(f"[Scheduler] ✅ Cycle terminé — {len(ranking_cache)} coins — {last_update}")

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
