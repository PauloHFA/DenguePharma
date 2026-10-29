from __future__ import annotations
import re

def text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def year(value):
    if not isinstance(value, str):
        return None
    match = re.match(r"^(\d{4})(?:\D|$)", value)
    return int(match[1]) if match and 1800 <= int(match[1]) <= 2200 else None


def identifier(kind, value):
    value = text(value)
    if not value:
        return None
    if kind == "DOI":
        value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value, flags=re.I).lower()
    else:
        value = value.upper()
    return f"{kind}:{value}"


def document_identifiers(document):
    metadata = document.get("metadata", {})
    ids = [identifier(k, metadata.get(n)) for k, n in (("PMID", "pmid"), ("DOI", "doi"), ("PMCID", "pmcid"))]
    nct = metadata.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    if nct:
        ids.append(identifier("NCT", nct))
    return sorted(set(i for i in ids if i))
