"""
Service DexScreener : récupère la liquidité USD maximale
parmi toutes les paires d'un token sur les DEX.
"""

import requests
from config import DEXSCREENER_BASE, TIMEOUT_DEX


def _liquidity_from_pairs(pairs: list) -> float:
    if not pairs:
        return 0.0
    return max((p.get("liquidity", {}).get("usd") or 0) for p in pairs)


def get_best_liquidity(symbol: str, contract_addresses: dict | None = None) -> float:
    """
    Cherche le token par symbole sur DexScreener.
    Si le symbole est trop court (< 2 chars), utilise les adresses de contrat à la place.
    Retourne la liquidité USD de la meilleure paire (la plus liquide).
    Retourne 0.0 si aucune paire trouvée ou erreur.
    """
    # Symbole trop court → fallback sur adresse de contrat
    if not symbol or len(symbol) < 2:
        if not contract_addresses:
            return 0.0
        return _get_liquidity_by_contract(contract_addresses)

    try:
        response = requests.get(
            f"{DEXSCREENER_BASE}/search",
            params={"q": symbol},
            timeout=TIMEOUT_DEX,
        )
        response.raise_for_status()
        return _liquidity_from_pairs(response.json().get("pairs") or [])

    except requests.RequestException as e:
        print(f"[DexScreener] Erreur {symbol}: {e}")
        return 0.0


def _get_liquidity_by_contract(platforms: dict) -> float:
    """
    Interroge DexScreener via adresse de contrat pour les tokens à symbole trop court.
    `platforms` est le dict CoinGecko : {"ethereum": "0x...", "bsc": "0x...", ...}
    """
    for chain, address in platforms.items():
        if not address:
            continue
        try:
            response = requests.get(
                f"{DEXSCREENER_BASE}/tokens/{address}",
                timeout=TIMEOUT_DEX,
            )
            response.raise_for_status()
            liquidity = _liquidity_from_pairs(response.json().get("pairs") or [])
            if liquidity > 0:
                return liquidity
        except requests.RequestException as e:
            print(f"[DexScreener] Erreur contrat {address}: {e}")
    return 0.0
