import sys
from typing import Optional

from .config import MAILTO


def _reconstruct_abstract(inverted_index: dict) -> Optional[str]:
    if not inverted_index:
        return None
    try:
        max_pos = max(pos for positions in inverted_index.values() for pos in positions)
        words = [""] * (max_pos + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        text = " ".join(words).strip()
        return text if text else None
    except Exception:
        return None


def _normalize_work_id(work_id: str) -> str:
    if not work_id or not work_id.strip():
        return ""
    work_id = work_id.strip()
    if work_id.startswith("https://openalex.org/"):
        return work_id
    if work_id.upper().startswith("W") and len(work_id) > 1:
        return f"https://openalex.org/{work_id.upper()}"
    if work_id.lower().startswith("doi:"):
        return f"https://doi.org/{work_id[4:]}"
    if work_id.startswith("https://doi.org/"):
        return work_id
    if work_id.startswith("10."):
        return f"https://doi.org/{work_id}"
    if work_id.lower().startswith("pmid:"):
        return f"https://pubmed.ncbi.nlm.nih.gov/{work_id[5:]}"
    return work_id


def _normalize_author_id(author_id: str) -> str:
    if not author_id or not author_id.strip():
        return ""
    author_id = author_id.strip()
    if author_id.startswith("https://openalex.org/"):
        return author_id
    if author_id.upper().startswith("A") and len(author_id) > 1:
        return f"https://openalex.org/{author_id.upper()}"
    if author_id.startswith("https://orcid.org/"):
        return author_id
    if author_id.lower().startswith("orcid:"):
        return f"https://orcid.org/{author_id[6:]}"
    if author_id.lower().startswith("0000") and len(author_id) == 19:
        return f"https://orcid.org/{author_id}"
    return author_id


def _build_filter_string(filters: dict) -> str:
    parts = []
    for key, value in filters.items():
        if value is not None:
            parts.append(f"{key}:{value}")
    return ",".join(parts)
