"""
Moteur de scoring complet.
Chaque métrique retourne un float [0, 1].
"""
import math
from config import WEIGHTS, NARRATIVE_KEYWORDS


# ── Métriques de base ──────────────────────────────────────────────────────────

def low_cap_score(market_cap: float) -> float:
    """Courbe log : 100k$ → 1.0 / 50M$ → 0.0"""
    if market_cap <= 0:
        return 0.0
    low  = math.log10(100_000)
    high = math.log10(50_000_000)
    val  = math.log10(max(market_cap, 100_000))
    return max(0.0, (high - val) / (high - low))


def liquidity_score(liquidity: float, market_cap: float) -> float:
    """liquidity / market_cap, plafonné à 1."""
    if market_cap <= 0:
        return 0.0
    return min(liquidity / market_cap, 1.0)


def volume_score(volume_24h: float, liquidity: float) -> float:
    """
    Ratio volume/liquidité :
    <1 → 0.3 | 1-3 → 0.7 | 3-6 → 1.0 | >6 → 0.5 (wash trading suspect)
    """
    if liquidity <= 0:
        return 0.0
    ratio = volume_24h / liquidity
    if ratio < 1:   return 0.3
    if ratio < 3:   return 0.7
    if ratio <= 6:  return 1.0
    return 0.5


def dev_score(dev_data: dict) -> float:
    """Commits du dernier mois / 30, plafonné à 1."""
    commits = (dev_data.get("commit_count_4_weeks") or
               dev_data.get("commits_last_month") or 0)
    # Fallback : stars + forks si pas de commits
    if commits == 0:
        stars = dev_data.get("stars") or 0
        forks = dev_data.get("forks") or 0
        return min((stars + forks * 2) / 500, 1.0)
    return min(commits / 30, 1.0)


def community_score(community_data: dict) -> float:
    """Twitter followers / 50k, plafonné à 1."""
    followers = (community_data.get("twitter_followers") or 0)
    return min(followers / 50_000, 1.0)


def holder_score(holders_today: int, holders_week: int) -> float:
    """Croissance holders sur 7 jours × 5, plafonné à 1."""
    if holders_week <= 0:
        return 0.0
    growth = (holders_today - holders_week) / holders_week
    return min(max(growth * 5, 0.0), 1.0)


# ── Module CEX Pre-listing ─────────────────────────────────────────────────────

def cex_listing_score(
    dex_volume: float,
    liquidity: float,
    holder_growth: float,
    dev: float,
    twitter_followers: int,
    pair_age_days: float,
) -> float:
    score = 0.0
    if dex_volume > 5_000_000:    score += 0.3
    if liquidity > 2_000_000:     score += 0.2
    if holder_growth > 0.20:      score += 0.2
    if dev > 0.5:                 score += 0.1
    if twitter_followers > 10_000: score += 0.1
    if pair_age_days > 30:        score += 0.1
    return min(score, 1.0)


# ── Module Whale Activity ──────────────────────────────────────────────────────

def whale_activity_score(whale_buy: float, whale_sell: float, new_whales: bool = False) -> float:
    """
    whale_ratio = buy / (sell + 1)
    <1 → 0.2 | 1-2 → 0.5 | 2-4 → 0.8 | >4 → 1.0
    Bonus +0.2 si nouveaux whales détectés sur 7j.
    """
    ratio = whale_buy / (whale_sell + 1)
    if ratio < 1:   base = 0.2
    elif ratio < 2: base = 0.5
    elif ratio <= 4: base = 0.8
    else:           base = 1.0
    return min(base + (0.2 if new_whales else 0.0), 1.0)


# ── Module Narratives ──────────────────────────────────────────────────────────

def narrative_score(description: str, categories: list, mentions_today: int = 0, mentions_week: int = 1) -> tuple[str, float]:
    """
    Détecte la narrative dominante et calcule un score.
    Retourne (dominant_narrative, score).
    """
    text = (description + " " + " ".join(categories)).lower()
    counts = {}
    for narrative, keywords in NARRATIVE_KEYWORDS.items():
        counts[narrative] = sum(text.count(kw) for kw in keywords)

    total = sum(counts.values()) or 1
    dominant = max(counts, key=counts.get)
    base_score = counts[dominant] / total

    # Trending score
    if mentions_week > 0:
        growth = (mentions_today - mentions_week) / mentions_week
    else:
        growth = 0
    if growth < 0.10:   trend = 0.2
    elif growth < 0.30: trend = 0.5
    elif growth < 0.70: trend = 0.8
    else:               trend = 1.0

    score = base_score * 0.6 + trend * 0.4
    return dominant, round(score, 4)


# ── Module Manipulation ────────────────────────────────────────────────────────

def manipulation_score(
    volume_24h: float,
    liquidity: float,
    holders: int,
    top10_pct: float,
    dev_commits: int,
    pair_age_days: float,
) -> float:
    penalty = 0.0
    if liquidity > 0:
        ratio = volume_24h / liquidity
        if 10 <= ratio < 30: penalty += 0.1   # suspicion
        elif ratio >= 30:    penalty += 0.3   # manipulation probable
    if holders < 200:        penalty += 0.2
    if top10_pct > 60:       penalty += 0.2
    if dev_commits == 0:     penalty += 0.2
    if pair_age_days < 7:    penalty += 0.2
    return min(penalty, 1.0)


# ── Score final ────────────────────────────────────────────────────────────────

def compute_score(coin: dict) -> float:
    mc          = coin.get("market_cap") or 1
    vol         = coin.get("volume_24h") or 0
    liq         = coin.get("liquidity") or 0
    dex_vol     = coin.get("dex_volume_24h") or vol
    dev_data    = coin.get("dev_data") or {}
    community   = coin.get("community_data") or {}
    holders_now = coin.get("holders_today") or 0
    holders_7d  = coin.get("holders_week") or 0
    pair_age    = coin.get("pair_age_days") or 999
    twitter     = community.get("twitter_followers") or 0
    top10_pct   = coin.get("top10_wallets_pct") or 0
    whale_buy   = coin.get("whale_buy_volume") or 0
    whale_sell  = coin.get("whale_sell_volume") or 0
    description = coin.get("description") or ""
    categories  = coin.get("categories") or []

    dev   = dev_score(dev_data)
    comm  = community_score(community)
    commits = (dev_data.get("commit_count_4_weeks") or
               dev_data.get("commits_last_month") or 0)

    h_growth = (holders_now - holders_7d) / holders_7d if holders_7d > 0 else 0
    h_score  = holder_score(holders_now, holders_7d)

    dominant_narrative, narr_score = narrative_score(description, categories)
    manip  = manipulation_score(vol, liq, holders_now, top10_pct, commits, pair_age)
    whale  = whale_activity_score(whale_buy, whale_sell)
    cex    = cex_listing_score(dex_vol, liq, h_growth, dev, twitter, pair_age)

    raw = (
        low_cap_score(mc)        * WEIGHTS["low_cap"]      +
        liquidity_score(liq, mc) * WEIGHTS["liquidity"]    +
        volume_score(vol, liq)   * WEIGHTS["volume"]       +
        h_score                  * WEIGHTS["holder"]       +
        dev                      * WEIGHTS["dev"]          +
        comm                     * WEIGHTS["community"]    +
        cex                      * WEIGHTS["cex_listing"]  +
        whale                    * WEIGHTS["whale"]        +
        narr_score               * WEIGHTS["narrative"]    +
        (1 - manip)              * WEIGHTS["manipulation"]
    ) * 100

    final = raw * (1 - manip)

    # Pénalités
    if liq > 0 and liq < 100_000: final *= 0.3
    if dev == 0:                   final *= 0.6
    if holders_now > 0 and holders_now < 200: final *= 0.5

    # Stocker les sous-scores pour l'affichage
    coin["_scores"] = {
        "dominant_narrative":        dominant_narrative,
        "narrative_score":           round(narr_score, 3),
        "whale_activity_score":      round(whale, 3),
        "cex_listing_potential_score": round(cex, 3),
        "manipulation_score":        round(manip, 3),
    }

    return round(final, 2)
