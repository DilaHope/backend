"""
Calcul du score de potentiel d'une crypto.
Chaque composante est normalisée entre 0 et 1 avant application du poids.

Profil idéal :
  - market cap très basse (proche de 100k$)
  - volume élevé par rapport à sa cap
  - bonne liquidité DEX
  - activité GitHub
  - communauté Twitter
"""

from config import WEIGHTS


def dev_score(dev_data: dict) -> float:
    """Score GitHub : stars + forks*2, normalisé sur 500 (seuil réaliste small cap)."""
    if not dev_data:
        return 0.0
    stars = dev_data.get("stars") or 0
    forks = dev_data.get("forks") or 0
    return min((stars + forks * 2) / 500, 1.0)


def community_score(community_data: dict) -> float:
    """Score communauté : Twitter followers normalisé sur 50k (seuil small cap)."""
    if not community_data:
        return 0.0
    followers = community_data.get("twitter_followers") or 0
    return min(followers / 50_000, 1.0)


def low_cap_score(market_cap: float) -> float:
    """
    Courbe logarithmique : favorise fortement les très petites caps.
    100k$ → 1.0 / 1M$ → 0.8 / 10M$ → 0.5 / 100M$ → 0.0
    """
    import math
    if market_cap <= 0:
        return 0.0
    low  = math.log(100_000)    # borne basse
    high = math.log(100_000_000)  # borne haute
    val  = math.log(max(market_cap, 100_000))
    return max(0.0, (high - val) / (high - low))


def volume_score(volume_24h: float, market_cap: float) -> float:
    """Ratio volume/MC : momentum. Normalisé sur 0.5 (50% de la cap = excellent)."""
    if market_cap <= 0:
        return 0.0
    return min(volume_24h / market_cap / 0.5, 1.0)


def liquidity_score(liquidity_usd: float, market_cap: float) -> float:
    """
    Ratio liquidité DEX / market cap (plus pertinent que /FDV pour les small caps).
    10% de la cap en liquidité = score max.
    """
    if market_cap <= 0:
        return 0.0
    return min(liquidity_usd / market_cap / 0.10, 1.0)


def compute_score(
    market_cap: float,
    volume_24h: float,
    fdv: float,
    liquidity_usd: float,
    dev_data: dict,
    community_data: dict,
) -> float:
    """
    Score final entre 0 et 100.
    Chaque composante est [0,1] × son poids, puis multiplié par 100.
    """
    score = (
        low_cap_score(market_cap)                * WEIGHTS["low_cap"]    +
        volume_score(volume_24h, market_cap)     * WEIGHTS["volume"]     +
        liquidity_score(liquidity_usd, market_cap) * WEIGHTS["liquidity"] +
        dev_score(dev_data)                      * WEIGHTS["dev"]        +
        community_score(community_data)          * WEIGHTS["community"]
    )
    return round(score * 100, 2)
