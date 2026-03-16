"""
Service CoinGecko : liste des coins (market cap, volume, supply)
et détail d'un coin (dev_data, community_data, platforms).
"""

import time
import requests
from config import COINGECKO_BASE, COINS_PER_PAGE, MAX_MARKET_CAP, TIMEOUT_DEFAULT, TIMEOUT_DETAIL


def _get_with_retry(url: str, params: dict, timeout: int, retries: int = 3) -> dict | list | None:
    """GET avec retry automatique sur 429 (rate limit)."""
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 429:
                wait = 60 if attempt == 0 else 120
                print(f"[CoinGecko] Rate limit 429 — attente {wait}s (tentative {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[CoinGecko] Erreur requête: {e}")
            if attempt < retries - 1:
                time.sleep(10)
    return None


def get_small_cap_coins(pages: int = 4) -> list[dict]:
    """
    Récupère les coins triés par market cap décroissante, filtrés sous MAX_MARKET_CAP.
    On prend les pages du bas (small caps) en cherchant dans les pages élevées.
    Retourne une liste de dicts bruts CoinGecko.
    """
    coins = []
    for page in range(1, pages + 1):
        data = _get_with_retry(
            f"{COINGECKO_BASE}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": COINS_PER_PAGE,
                "page": page,
                "sparkline": "false",
            },
            timeout=TIMEOUT_DEFAULT,
        )

        if not data:
            break

        for coin in data:
            mc = coin.get("market_cap") or 0
            if 100_000 < mc < MAX_MARKET_CAP:  # entre 100k$ et 100M$
                coins.append(coin)

        print(f"[CoinGecko] Page {page} — {len(data)} coins récupérés, {len(coins)} small caps au total")
        time.sleep(2)  # respect rate limit CoinGecko free

    return coins


def get_coin_detail(coin_id: str) -> dict:
    """
    Récupère le détail d'un coin : developer_data, community_data, platforms.
    Retourne un dict vide en cas d'erreur.
    """
    data = _get_with_retry(
        f"{COINGECKO_BASE}/coins/{coin_id}",
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "true",
            "developer_data": "true",
        },
        timeout=TIMEOUT_DETAIL,
    )
    return data if isinstance(data, dict) else {}
