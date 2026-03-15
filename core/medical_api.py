import json
import os
from urllib import error, parse, request


def _enabled():
    return os.environ.get("MEDICAL_API_ENABLED", "0") == "1"


def _fetch_json(url, timeout=8):
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_rxcui(drug_name):
    if not drug_name:
        return None
    safe_name = parse.quote(drug_name.strip())
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={safe_name}&search=2"
    try:
        data = _fetch_json(url)
    except (error.URLError, error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None
    ids = data.get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None


def fetch_drug_interactions(drug_names):
    """
    Fetch interaction narratives from RxNav API.
    Returns [] when disabled or unavailable.
    """
    if not _enabled():
        return []

    normalized = []
    for name in drug_names:
        cleaned = (name or "").strip()
        if cleaned:
            normalized.append(cleaned)

    if len(normalized) < 2:
        return []

    rxcuis = []
    for name in normalized:
        rxcui = _resolve_rxcui(name)
        if rxcui:
            rxcuis.append(rxcui)

    unique_rxcuis = list(dict.fromkeys(rxcuis))
    if len(unique_rxcuis) < 2:
        return []

    url = f"https://rxnav.nlm.nih.gov/REST/interaction/list.json?rxcuis={'+'.join(unique_rxcuis)}"
    try:
        data = _fetch_json(url)
    except (error.URLError, error.HTTPError, json.JSONDecodeError, TimeoutError):
        return []

    alerts = []
    groups = data.get("fullInteractionTypeGroup", [])
    for group in groups:
        for interaction_type in group.get("fullInteractionType", []):
            for pair in interaction_type.get("interactionPair", []):
                description = (pair.get("description") or "").strip()
                if description:
                    alerts.append(description)

    # Deduplicate and limit payload size.
    unique_alerts = list(dict.fromkeys(alerts))
    return unique_alerts[:5]
