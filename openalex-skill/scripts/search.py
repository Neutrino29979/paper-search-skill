from typing import Optional

from .api import paginate, request
from .extractors import extract_author_brief, extract_institution_brief, extract_work_brief
from .synonyms import expand_query
from .utils import _build_filter_string, _normalize_author_id


def search_works(
    query: str = "",
    year: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    author_id: Optional[str] = None,
    institution_id: Optional[str] = None,
    concept_id: Optional[str] = None,
    source: Optional[str] = None,
    sort: Optional[str] = None,
    per_page: int = 25,
    page: int = 1,
    max_results: Optional[int] = None,
    min_citations: Optional[int] = None,
    open_access: Optional[bool] = None,
    type_filter: Optional[str] = None,
    select: Optional[list] = None,
) -> dict:
    if max_results is not None and max_results > per_page:
        return _search_works_paginated(
            query=query, year=year, year_from=year_from, year_to=year_to,
            author_id=author_id, institution_id=institution_id,
            concept_id=concept_id, source=source, sort=sort,
            per_page=per_page, max_results=max_results,
            min_citations=min_citations, open_access=open_access,
            type_filter=type_filter, select=select,
        )

    endpoint = "/works"

    filters = {}
    if year:
        filters["publication_year"] = year
    if year_from:
        filters["from_publication_date"] = f"{year_from}-01-01"
    if year_to:
        filters["to_publication_date"] = f"{year_to}-12-31"
    if author_id:
        normalized = _normalize_author_id(author_id)
        filters["authorships.author.id"] = normalized
    if institution_id:
        filters["authorships.institutions.id"] = institution_id
    if concept_id:
        filters["concepts.id"] = concept_id
    if min_citations is not None:
        filters["cited_by_count"] = f">{min_citations}"
    if open_access is not None:
        filters["open_access.is_oa"] = str(open_access).lower()
    if type_filter:
        filters["type"] = type_filter
    if source:
        filters["primary_location.source.id"] = source

    params = {"per_page": min(per_page, 200), "page": page}
    if query:
        params["search"] = query
    if filters:
        params["filter"] = _build_filter_string(filters)
    if sort:
        params["sort"] = sort
    if select:
        params["select"] = ",".join(select)

    data = request(endpoint, params)
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


def _search_works_paginated(
    query: str = "",
    year: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    author_id: Optional[str] = None,
    institution_id: Optional[str] = None,
    concept_id: Optional[str] = None,
    source: Optional[str] = None,
    sort: Optional[str] = None,
    per_page: int = 25,
    max_results: int = 200,
    min_citations: Optional[int] = None,
    open_access: Optional[bool] = None,
    type_filter: Optional[str] = None,
    select: Optional[list] = None,
) -> dict:
    filters = {}
    if year:
        filters["publication_year"] = year
    if year_from:
        filters["from_publication_date"] = f"{year_from}-01-01"
    if year_to:
        filters["to_publication_date"] = f"{year_to}-12-31"
    if author_id:
        normalized = _normalize_author_id(author_id)
        filters["authorships.author.id"] = normalized
    if institution_id:
        filters["authorships.institutions.id"] = institution_id
    if concept_id:
        filters["concepts.id"] = concept_id
    if min_citations is not None:
        filters["cited_by_count"] = f">{min_citations}"
    if open_access is not None:
        filters["open_access.is_oa"] = str(open_access).lower()
    if type_filter:
        filters["type"] = type_filter
    if source:
        filters["primary_location.source.id"] = source

    params = {"per_page": min(per_page, 200)}
    if query:
        params["search"] = query
    if filters:
        params["filter"] = _build_filter_string(filters)
    if sort:
        params["sort"] = sort
    if select:
        params["select"] = ",".join(select)

    paginated = paginate("/works", params, max_results=max_results)
    if paginated.get("error"):
        return paginated

    raw = paginated.get("results", [])
    results = [extract_work_brief(w) for w in raw]
    return {
        "results": results,
        "total": len(results),
        "per_page": per_page,
        "page": 1,
    }


def search_works_with_expansion(
    query: str = "",
    llm_synonyms: list = None,
    always_expand: bool = False,
    **kwargs
) -> dict:
    expanded = expand_query(query)

    if llm_synonyms:
        for syn in llm_synonyms:
            if syn.strip().lower() not in [q.strip().lower() for q in expanded]:
                expanded.append(syn.strip())

    all_results = []
    seen_ids = set()
    per_page = kwargs.get("per_page", 25)
    target = kwargs.get("max_results", per_page)

    for i, variant in enumerate(expanded):
        result = search_works(query=variant, **kwargs)
        if result.get("error"):
            if i == 0:
                return result
            continue

        items = result.get("results", [])
        for item in items:
            item_id = item.get("id", "")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                all_results.append(item)

        if not always_expand and len(all_results) >= target:
            break

    all_results.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)

    return {
        "results": all_results[:target],
        "total": len(all_results),
        "expansions_used": expanded,
        "note": (
            f"已合并 {len(expanded)} 个查询变体的结果"
            if len(expanded) > 1
            else ""
        ),
    }


def search_authors(
    query: str = "",
    institution_id: Optional[str] = None,
    concept_id: Optional[str] = None,
    per_page: int = 25,
    page: int = 1,
    min_works: Optional[int] = None,
    min_citations: Optional[int] = None,
    select: Optional[list] = None,
) -> dict:
    endpoint = "/authors"

    filters = {}
    if institution_id:
        filters["last_known_institutions.id"] = institution_id
    if concept_id:
        filters["concepts.id"] = concept_id
    if min_works is not None:
        filters["works_count"] = f">{min_works}"
    if min_citations is not None:
        filters["cited_by_count"] = f">{min_citations}"

    params = {"per_page": min(per_page, 200), "page": page}
    if query:
        params["search"] = query
    if filters:
        params["filter"] = _build_filter_string(filters)
    if select:
        params["select"] = ",".join(select)

    data = request(endpoint, params)
    if data.get("error"):
        return data

    meta = data.get("meta", {})
    results_raw = data.get("results", [])

    results = [extract_author_brief(a) for a in results_raw]

    return {
        "results": results,
        "total": meta.get("count", 0),
        "per_page": meta.get("per_page", per_page),
        "page": meta.get("page", page),
    }


def search_institutions(
    query: str = "",
    country_code: Optional[str] = None,
    type_filter: Optional[str] = None,
    per_page: int = 25,
    page: int = 1,
    select: Optional[list] = None,
) -> dict:
    endpoint = "/institutions"

    filters = {}
    if country_code:
        filters["country_code"] = country_code
    if type_filter:
        filters["type"] = type_filter

    params = {"per_page": min(per_page, 200), "page": page}
    if query:
        params["search"] = query
    if filters:
        params["filter"] = _build_filter_string(filters)
    if select:
        params["select"] = ",".join(select)

    data = request(endpoint, params)
    if data.get("error"):
        return data

    meta = data.get("meta", {})
    results_raw = data.get("results", [])

    results = [extract_institution_brief(inst) for inst in results_raw]

    return {
        "results": results,
        "total": meta.get("count", 0),
        "per_page": meta.get("per_page", per_page),
        "page": meta.get("page", page),
    }


def search_concepts(
    query: str = "",
    level: Optional[int] = None,
    per_page: int = 25,
    page: int = 1,
    select: Optional[list] = None,
) -> dict:
    endpoint = "/concepts"

    filters = {}
    if level is not None:
        filters["level"] = level

    params = {"per_page": min(per_page, 200), "page": page}
    if query:
        params["search"] = query
    if filters:
        params["filter"] = _build_filter_string(filters)
    if select:
        params["select"] = ",".join(select)

    data = request(endpoint, params)
    if data.get("error"):
        return data

    meta = data.get("meta", {})
    results_raw = data.get("results", [])

    results = []
    for c in results_raw:
        results.append({
            "id": c.get("id", ""),
            "name": c.get("display_name", ""),
            "level": c.get("level"),
            "description": c.get("description", ""),
            "works_count": c.get("works_count", 0),
            "cited_by_count": c.get("cited_by_count", 0),
            "image_url": c.get("image_url", ""),
            "parents": [p.get("display_name", "") for p in (c.get("ancestors") or [])],
        })

    return {
        "results": results,
        "total": meta.get("count", 0),
        "per_page": meta.get("per_page", per_page),
        "page": meta.get("page", page),
    }
