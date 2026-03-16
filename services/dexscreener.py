"""
DexScreener : liquidité, volume DEX, age des paires.
"""
import requests
from config import DEXSCREENER_BASE, TIMEOUT_DEX
from datetime import datetime, timezone


def _best_pair(pairs: list) -> dict:
    """Retourne la paire avec la liquidité maximale."""
    if not pairs:
        return {}
    return max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)


def _pair_age_days(pair: dict) -> float:
    """Calcule l'âge de la paire en jours depuis sa création."""
    created_ms = pair.get("pairCreatedAt")
    if not created_ms:
        return 999
    created = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
    return (datetime.now(tz=timezone.utc) - created).days


def _fetch_pairs(query: str) -> list:
    try:
        r = requests.get(
            f"{DEXSCREENER_BASE}/search",
            params={"q": query},
            timeout=TIMEOUT_DEX,
        )
        r.raise_for_status()
        return r.json().get("pairs") or []
    except requests.RequestException:
        return []


def _fetch_pairs_by_address(address: str) -> list:
    try:
        r = requests.get(
            f"{DEXSCREENER_BASE}/tokens/{address}",
            timeout=TIMEOUT_DEX,
        )
        r.raise_for_status()
        return r.json().get("pairs") or []
    except requests.RequestException:
        return []


def get_dex_data(symbol: str, platforms: dict | None = None) -> dict:
    """
    Retourne : liquidity, dex_volume_24h, pair_age_days.
    Fallback sur adresse de contrat si symbole trop court.
    """
    pairs = []

    if symbol and len(symbol) >= 2:
        pairs = _fetch_pairs(symbol)

    if not pairs and platforms:
        for address in platforms.values():
            if address:
                pairs = _fetch_pairs_by_address(address)
                if pairs:
                    break

    if not pairs:
        return {"liquidity": 0.0, "dex_volume_24h": 0.0, "pair_age_days": 999}

    best = _best_pair(pairs)
    total_volume = sum((p.get("volume") or {}).get("h24") or 0 for p in pairs)

    return {
        "liquidity":     (best.get("liquidity") or {}).get("usd") or 0.0,
        "dex_volume_24h": total_volume,
        "pair_age_days": _pair_age_days(best),
    }
