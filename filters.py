"""
Filtres appliqués avant scoring.
"""
from config import (
    MIN_MARKET_CAP, MAX_MARKET_CAP,
    MIN_LIQUIDITY, MIN_VOLUME,
    STABLECOIN_KEYWORDS,
)


def is_valid(coin: dict) -> bool:
    symbol = (coin.get("symbol") or "").lower()
    name   = (coin.get("name") or "").lower()

    # Exclure stablecoins
    if any(k in symbol or k in name for k in STABLECOIN_KEYWORDS):
        return False

    mc  = coin.get("market_cap") or 0
    vol = coin.get("volume_24h") or 0
    liq = coin.get("liquidity") or 0

    if not (MIN_MARKET_CAP < mc < MAX_MARKET_CAP):
        return False
    if vol < MIN_VOLUME:
        return False
    if liq > 0 and liq < MIN_LIQUIDITY:
        return False

    return True
