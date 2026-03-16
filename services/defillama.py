"""
DefiLlama : TVL des protocoles DeFi.
"""
import requests
from config import DEFILLAMA_BASE, TIMEOUT_DEFAULT

_protocols_cache: list[dict] = []


def _load_protocols() -> list[dict]:
    global _protocols_cache
    if _protocols_cache:
        return _protocols_cache
    try:
        r = requests.get(f"{DEFILLAMA_BASE}/protocols", timeout=TIMEOUT_DEFAULT)
        r.raise_for_status()
        _protocols_cache = r.json()
    except Exception:
        _protocols_cache = []
    return _protocols_cache


def get_tvl_for_symbol(symbol: str) -> float:
    """Cherche le TVL d'un token par son symbole dans la liste DefiLlama."""
    protocols = _load_protocols()
    sym = symbol.lower()
    for p in protocols:
        if (p.get("symbol") or "").lower() == sym:
            return float(p.get("tvl") or 0.0)
    return 0.0
