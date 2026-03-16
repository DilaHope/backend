"""
CoinGecko : markets + détail (dev, community, platforms, categories, description).
"""
import time
import requests
from config import COINGECKO_BASE, COINS_PER_PAGE, MAX_MARKET_CAP, MIN_MARKET_CAP, TIMEOUT_DEFAULT, TIMEOUT_DETAIL


def _get(url: str, params: dict, timeout: int, retries: int = 3):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"[CoinGecko] Rate limit — attente {wait}s (tentative {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"[CoinGecko] Erreur: {e}")
            if attempt < retries - 1:
                time.sleep(10)
    return None


def get_small_cap_coins(pages: int = 4) -> list[dict]:
    coins = []
    for page in range(1, pages + 1):
        data = _get(
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
            if MIN_MARKET_CAP < mc < MAX_MARKET_CAP:
                coins.append(coin)
        print(f"[CoinGecko] Page {page} — {len(data)} coins, {len(coins)} small caps")
        time.sleep(2)
    return coins


def get_coin_detail(coin_id: str) -> dict:
    data = _get(
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
