"""
Configuration centrale : URLs des APIs, poids du scoring, limites.
"""

# APIs
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
DEFILLAMA_BASE = "https://api.llama.fi"

# Filtres
MAX_MARKET_CAP = 100_000_000   # On ne garde que les < 100M$
COINS_PAGES = 4                # 4 pages x 250 = 1000 coins analysés
COINS_PER_PAGE = 250

# Scheduler
REFRESH_INTERVAL_MINUTES = 15

# Poids du score (total = 1.0)
WEIGHTS = {
    "low_cap":    0.30,   # Courbe log : favorise fortement les très petites caps
    "volume":     0.25,   # Volume/MC ratio → momentum (normalisé sur 50% de la cap)
    "liquidity":  0.20,   # Liquidité DEX / MC → tokenomics sains
    "dev":        0.12,   # Activité GitHub (stars + forks)
    "community":  0.13,   # Followers Twitter
}

# Timeouts HTTP (secondes)
TIMEOUT_DEFAULT = 10
TIMEOUT_DETAIL  = 8
TIMEOUT_DEX     = 5
