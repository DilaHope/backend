"""
Service DefiLlama : récupère le TVL (Total Value Locked) d'un protocole DeFi.
Utile pour les projets DeFi afin de mesurer l'utilité réelle.
"""

import requests
from config import DEFILLAMA_BASE, TIMEOUT_DEFAULT


def get_tvl(protocol_slug: str) -> float:
    """
    Récupère le TVL actuel d'un protocole via son slug DefiLlama.
    Retourne 0.0 si le protocole n'est pas trouvé ou en cas d'erreur.

    Exemple de slug : "uniswap", "aave", "curve"
    """
    try:
        response = requests.get(
            f"{DEFILLAMA_BASE}/protocol/{protocol_slug}",
            timeout=TIMEOUT_DEFAULT,
        )
        response.raise_for_status()
        data = response.json()
        return float(data.get("tvl") or 0.0)
    except requests.RequestException as e:
        print(f"[DefiLlama] Erreur {protocol_slug}: {e}")
        return 0.0


def get_all_protocols() -> list[dict]:
    """
    Récupère la liste complète des protocoles DefiLlama.
    Utile pour construire un mapping coin_id → slug.
    """
    try:
        response = requests.get(f"{DEFILLAMA_BASE}/protocols", timeout=TIMEOUT_DEFAULT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[DefiLlama] Erreur liste protocoles: {e}")
        return []
