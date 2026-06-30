from typing import Optional

from .api import batch_get_authors, batch_get_works, paginate, request
from .detail import get_author_detail, get_author_works, get_work_detail
from .extractors import extract_work_brief
from .utils import _build_filter_string, _normalize_author_id, _normalize_work_id


def _get_work_referenced_ids(work_id: str) -> list:
    work_id = _normalize_work_id(work_id)
    if not work_id:
        return []
    data = request(f"/works/{work_id}", {"select": "referenced_works"})
    if data.get("error"):
        return []
    return data.get("referenced_works") or []


def get_citations(
    work_id: str,
    per_page: int = 25,
    page: int = 1,
    max_results: int = 200,
    select: Optional[list] = None,
) -> dict:
    work_id = _normalize_work_id(work_id)
    if not work_id:
        return {"error": True, "message": "论文ID不能为空", "results": []}

    filters = {"cites": work_id}

    if max_results is not None:
        if max_results > per_page:
            return _get_citations_paginated(
                work_id=work_id, per_page=per_page,
                max_results=max_results, select=select,
            )
        per_page = max_results

    params = {
        "filter": _build_filter_string(filters),
        "sort": "cited_by_count:desc",
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


def _get_citations_paginated(
    work_id: str,
    per_page: int = 25,
    max_results: int = 200,
    select: Optional[list] = None,
) -> dict:
    filters = {"cites": work_id}
    params = {
        "filter": _build_filter_string(filters),
        "sort": "cited_by_count:desc",
        "per_page": min(per_page, 200),
    }
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


def get_references(
    work_id: str,
    per_page: int = 25,
    page: int = 1,
) -> dict:
    work_id = _normalize_work_id(work_id)
    if not work_id:
        return {"error": True, "message": "论文ID不能为空", "results": []}

    ref_ids = _get_work_referenced_ids(work_id)

    if not ref_ids:
        return {"results": [], "total": 0, "per_page": per_page, "page": page}

    total = len(ref_ids)
    start = (page - 1) * per_page
    end = start + per_page
    batch_ids = ref_ids[start:end]

    results = batch_get_works(batch_ids)

    return {
        "results": results,
        "total": total,
        "per_page": per_page,
        "page": page,
    }


def get_related_works(
    work_id: str,
    max_results: int = 10,
) -> dict:
    work_id = _normalize_work_id(work_id)
    if not work_id:
        return {"error": True, "message": "论文ID不能为空", "results": []}

    data = request(f"/works/{work_id}", {"select": "related_works"})
    if data.get("error"):
        return data

    related_ids = (data.get("related_works") or [])[:max_results]

    results = batch_get_works(related_ids)

    return {
        "results": results,
        "total": len(results),
    }


def build_citation_network(
    work_id: str,
    direction: str = "both",
    depth: int = 1,
    max_nodes: int = 50,
    max_requests: Optional[int] = None,
) -> dict:
    work_id = _normalize_work_id(work_id)
    if not work_id:
        return {"error": True, "message": "论文ID不能为空", "nodes": [], "edges": []}

    if direction not in ("forward", "backward", "both"):
        return {"error": True, "message": "direction 参数错误（forward/backward/both）", "nodes": [], "edges": []}

    nodes = {}
    edges = []
    seen = set()
    api_calls = 0

    center = get_work_detail(work_id)
    api_calls += 1
    if center.get("error"):
        return {"error": center["message"], "nodes": [], "edges": []}

    center_data = center["result"]
    center_id = center_data.get("id", work_id)
    nodes[center_id] = {
        "id": center_id,
        "title": center_data.get("title", ""),
        "year": center_data.get("publication_year"),
        "cited_by_count": center_data.get("cited_by_count", 0),
        "authors": [a.get("name", "") for a in (center_data.get("authors") or [])],
        "type": "center",
    }
    seen.add(center_id)

    def add_work_node(work_result, node_type="related"):
        wid = work_result.get("id", "")
        if not wid or wid in seen:
            return wid if wid else None
        seen.add(wid)
        nodes[wid] = {
            "id": wid,
            "title": work_result.get("title", ""),
            "year": work_result.get("publication_year"),
            "cited_by_count": work_result.get("cited_by_count", 0),
            "authors": [a.get("name", "") for a in (work_result.get("authors") or [])],
            "type": node_type,
        }
        return wid

    if direction in ("backward", "both"):
        refs = get_references(work_id, per_page=max_nodes)
        api_calls += 1
        if not refs.get("error"):
            for ref in refs.get("results", []):
                ref_id = add_work_node(ref, "reference")
                if ref_id:
                    edges.append({"source": center_id, "target": ref_id, "type": "cites"})

                if depth >= 2 and ref_id:
                    if max_requests and api_calls >= max_requests:
                        break
                    ref_of_ref = get_references(ref_id, per_page=10)
                    api_calls += 1
                    if not ref_of_ref.get("error"):
                        for r2 in ref_of_ref.get("results", []):
                            r2_id = add_work_node(r2, "reference_depth2")
                            if r2_id and len(edges) < max_nodes * 2:
                                edges.append({"source": ref_id, "target": r2_id, "type": "cites"})

    if direction in ("forward", "both"):
        if not (max_requests and api_calls >= max_requests):
            cites = get_citations(work_id, per_page=max_nodes)
            api_calls += 1
            if not cites.get("error"):
                for citing in cites.get("results", []):
                    citing_id = add_work_node(citing, "citation")
                    if citing_id:
                        edges.append({"source": citing_id, "target": center_id, "type": "cites"})

                    if depth >= 2 and citing_id:
                        if max_requests and api_calls >= max_requests:
                            break
                        cites_of_cites = get_citations(citing_id, per_page=10)
                        api_calls += 1
                        if not cites_of_cites.get("error"):
                            for c2 in cites_of_cites.get("results", []):
                                c2_id = add_work_node(c2, "citation_depth2")
                                if c2_id and len(edges) < max_nodes * 2:
                                    edges.append({"source": c2_id, "target": citing_id, "type": "cites"})

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "center_id": center_id,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "depth": depth,
            "direction": direction,
            "api_calls_made": api_calls,
        }
    }


def build_coauthor_network(
    author_id: str,
    max_works: int = 50,
) -> dict:
    author_id = _normalize_author_id(author_id)
    if not author_id:
        return {"error": True, "message": "作者ID不能为空", "nodes": [], "edges": []}

    author_detail = get_author_detail(author_id)
    if author_detail.get("error"):
        return {"error": author_detail["message"], "nodes": [], "edges": []}

    author_name = author_detail.get("result", {}).get("name", "")

    works = get_author_works(author_id, sort="cited_by_count:desc", per_page=min(max_works, 200))
    if works.get("error"):
        return {"error": works["message"], "nodes": [], "edges": []}

    coauthor_count = {}

    for work in works.get("results", []):
        authors = work.get("authors") or []
        for a in authors:
            aid = a.get("id", "")
            aname = a.get("name", "")
            if aid and aid != author_id:
                if aid not in coauthor_count:
                    coauthor_count[aid] = {"name": aname, "count": 0, "institution": a.get("institution", "")}
                coauthor_count[aid]["count"] += 1

    sorted_coauthors = sorted(coauthor_count.items(), key=lambda x: x[1]["count"], reverse=True)

    nodes = []
    edges = []

    nodes.append({
        "id": author_id,
        "name": author_name or "目标作者",
        "works_count": author_detail.get("result", {}).get("works_count", 0),
        "is_center": True,
    })

    top_coauthors = sorted_coauthors[:30]
    batch_ids = [co_id for co_id, _ in top_coauthors]
    batch_info = batch_get_authors(batch_ids)

    for co_id, co_info in top_coauthors:
        co_brief = batch_info.get(co_id, {})
        co_works_count = co_brief.get("works_count", 0)
        co_h_index = co_brief.get("h_index", 0)

        nodes.append({
            "id": co_id,
            "name": co_info["name"],
            "institution": co_info.get("institution", ""),
            "works_count": co_works_count,
            "h_index": co_h_index,
            "coauthored_count": co_info["count"],
            "is_center": False,
        })

        edges.append({
            "source": author_id,
            "target": co_id,
            "works": co_info["count"],
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "center_id": author_id,
        "summary": {
            "total_coauthors": len(sorted_coauthors),
            "displayed_coauthors": len(nodes) - 1,
            "total_works_analyzed": len(works.get("results", [])),
        }
    }
