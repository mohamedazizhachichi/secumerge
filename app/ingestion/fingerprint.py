"""Calcul de l'empreinte stable d'un finding.

Deux rapports successifs signalant le même problème doivent produire la
même empreinte : scanner + identifiant de règle + fichier + position.

Le titre n'entre volontairement pas dans l'empreinte : un scanner peut le
reformuler sans que le problème ait changé.
"""

import hashlib


def compute_fingerprint(
    *,
    scanner: str,
    rule_id: str | None,
    file_path: str | None,
    location: str | None,
) -> str:
    """Empreinte SHA-256 déterministe (chemins normalisés avec « / »)."""
    normalized_path = (file_path or "").replace("\\", "/")
    material = "|".join([scanner, rule_id or "", normalized_path, location or ""])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
