"""
Configuration centrale.
"""
import os

# APIs
COINGECKO_BASE   = "https://api.coingecko.com/api/v3"
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
DEFILLAMA_BASE   = "https://api.llama.fi"

# Filtres
MIN_MARKET_CAP         = 100_000      # 100k$
MAX_MARKET_CAP         = 50_000_000   # 50M$
MIN_LIQUIDITY          = 200_000      # 200k$
MIN_VOLUME             = 50_000       # 50k$
STABLECOIN_KEYWORDS    = ["usd","usdt","usdc","dai","eur","busd","tusd","frax","lusd","gusd"]

# Collecte
COINS_PAGES    = 4
COINS_PER_PAGE = 250

# Scheduler
REFRESH_INTERVAL_MINUTES = 15

# Poids du score final (total = 1.0)
WEIGHTS = {
    "low_cap":       0.18,
    "liquidity":     0.15,
    "volume":        0.13,
    "holder":        0.10,
    "dev":           0.07,
    "community":     0.05,
    "cex_listing":   0.10,
    "whale":         0.10,
    "narrative":     0.07,
    "manipulation":  0.05,  # (1 - manipulation_score) * poids
}

# Narratives
NARRATIVE_KEYWORDS = {
    "AI":     ["ai", "artificial intelligence", "machine learning", "gpt", "llm"],
    "GAMING": ["game", "gaming", "play", "metaverse", "nft game"],
    "RWA":    ["real world asset", "tokenization", "rwa", "real estate"],
    "MEME":   ["meme", "dog", "inu", "pepe", "shib", "doge"],
    "DEFI":   ["defi", "dex", "lending", "yield", "swap", "amm"],
    "LAYER1": ["layer1", "l1", "validator", "consensus", "blockchain"],
    "LAYER2": ["layer2", "l2", "rollup", "zk", "optimism", "arbitrum"],
}

# Timeouts HTTP (secondes)
TIMEOUT_DEFAULT = 10
TIMEOUT_DETAIL  = 8
TIMEOUT_DEX     = 5
