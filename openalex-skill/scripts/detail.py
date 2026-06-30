from typing import Optional

from .api import request
from .extractors import extract_author_brief, extract_work_brief
from .utils import _normalize_author_id, _normalize_work_id, _reconstruct_abstract, _build_filter_string


def get_work_detail(work_id: str, select: Optional[list] = None) -> dict:
    work_id = _normalize_work_id(work_id)
    if not work_id:
        return {"error": True, "message": "论文ID不能为空", "result": None}

    endpoint = f"/works/{work_id}"
    params = {}
    if select:
        params["select"] = ",".join(select)

    data = request(endpoint, params)
    if data.get("error"):
        return data

    if not data or "id" not in data:
        return {"error": True, "message": "未找到该论文", "result": None}

    brief = extract_work_brief(data)

    authorships = data.get("authorships") or []
    full_authors = []
    for a in authorships:
        author_info = a.get("author") or {}
        inst_list = a.get("institutions") or []
        full_authors.append({
            "name": author_info.get("display_name", ""),
            "id": author_info.get("id", ""),
            "orcid": author_info.get("orcid", ""),
            "institutions": [
                {"name": i.get("display_name", ""), "id": i.get("id", ""), "country": i.get("country_code", "")}
                for i in inst_list
            ],
            "author_position": a.get("author_position", ""),
        })

    locations = data.get("locations") or []
    full_locations = []
    for loc in locations:
        source = loc.get("source") or {}
        full_locations.append({
            "source": source.get("display_name", ""),
            "source_id": source.get("id", ""),
            "issn": source.get("issn_l", ""),
            "is_oa": loc.get("is_oa", False),
            "landing_page_url": loc.get("landing_page_url", ""),
            "pdf_url": loc.get("pdf_url", ""),
            "license": loc.get("license", ""),
        })

    concepts = data.get("concepts") or []
    full_concepts = [
        {"name": c.get("display_name", ""), "score": c.get("score", 0), "level": c.get("level", 0)}
        for c in concepts
    ]

    referenced_works = data.get("referenced_works") or []
    related_works = data.get("related_works") or []

    full_abstract = _reconstruct_abstract(data.get("abstract_inverted_index"))

    result = {
        **brief,
        "abstract": full_abstract or "摘要不可用",
        "authors_full": full_authors,
        "locations": full_locations,
        "concepts": full_concepts,
        "referenced_works_count": len(referenced_works),
        "related_works_count": len(related_works),
        "referenced_works": referenced_works[:20],
        "related_works": related_works[:20],
        "publication_date": data.get("publication_date"),
        "keywords": data.get("keywords") or [],
        "mesh_terms": [m.get("display_name", "") for m in (data.get("mesh") or [])],
        "grants": data.get("grants") or [],
    }

    return {"result": result}


def get_author_detail(author_id: str, select: Optional[list] = None) -> dict:
    author_id = _normalize_author_id(author_id)
    if not author_id:
        return {"error": True, "message": "作者ID不能为空", "result": None}

    endpoint = f"/authors/{author_id}"
    params = {}
    if select:
        params["select"] = ",".join(select)

    data = request(endpoint, params)
    if data.get("error"):
        return data

    if not data or "id" not in data:
        return {"error": True, "message": "未找到该作者", "result": None}

    brief = extract_author_brief(data)

    institutions = data.get("last_known_institutions") or []
    full_institutions = [
        {"name": i.get("display_name", ""), "id": i.get("id", ""), "country": i.get("country_code", "")}
        for i in institutions
    ]

    concepts = data.get("x_concepts") or []
    full_concepts = [
        {"name": c.get("display_name", ""), "score": c.get("score", 0)}
        for c in concepts
    ]

    topics_raw = data.get("topics") or []
    full_topics = [
        {
            "name": t.get("display_name", ""),
            "subfield": (t.get("subfield") or {}).get("display_name", ""),
            "field": (t.get("field") or {}).get("display_name", ""),
            "domain": (t.get("domain") or {}).get("display_name", ""),
        }
        for t in topics_raw[:5]
    ]

    count_by_year = data.get("counts_by_year") or []

    result = {
        **brief,
        "institutions_full": full_institutions,
        "concepts": full_concepts,
        "topics": full_topics,
        "counts_by_year": [
            {"year": y.get("year"), "works": y.get("works_count", 0), "citations": y.get("cited_by_count", 0)}
            for y in count_by_year[:10]
        ],
        "works_api_url": data.get("works_api_url", ""),
        "updated_date": data.get("updated_date", ""),
    }

    return {"result": result}


def get_author_works(
    author_id: str,
    sort: str = "publication_year",
    per_page: int = 25,
    page: int = 1,
    select: Optional[list] = None,
) -> dict:
    author_id = _normalize_author_id(author_id)
    if not author_id:
        return {"error": True, "message": "作者ID不能为空", "results": []}

    filters = {"authorships.author.id": author_id}
    params = {
        "filter": _build_filter_string(filters),
        "sort": sort,
        "per_page": min(per_page, 200),
        "page": page,
    }
    if select:
        params["select"] = ",".join(select)

    data = request("/works", params)
    if data.get("error"):
        return data

    meta = data.get("meta", {})
    results_raw = data.get("results", [])

    results = [extract_work_brief(w) for w in results_raw]

    return {
        "results": results,
        "total": meta.get("count", 0),
        "per_page": meta.get("per_page", per_page),
        "page": meta.get("page", page),
    }
