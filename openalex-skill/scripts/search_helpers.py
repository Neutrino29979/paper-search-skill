from .api import request
from .detail import get_author_detail, get_author_works, get_work_detail
from .extractors import extract_author_brief
from .search import search_works


def find_author_by_paper(name: str, paper_title: str = "", doi: str = "") -> dict:
    """通过已知论文查找作者的正确 ID。

    这是应对 OpenAlex 作者级别数据缺失的最佳策略。
    先搜论文 → 从论文的 authorships 中提取作者 ID → 再获取完整画像。

    返回格式: {"found": True/False, "author_id": "...", "author": {...}, "paper": {...}}
    """
    query = paper_title or name
    if doi:
        query = doi

    result = search_works(query=query, per_page=10)
    if result.get("error"):
        return {"found": False, "error": result.get("message")}

    for work in result.get("results", []):
        paper_id = work.get("id", "")
        detail = get_work_detail(work_id=paper_id)
        if detail.get("error"):
            continue

        authors_full = detail.get("result", {}).get("authors_full", [])
        for author in authors_full:
            author_name = author.get("name", "").lower()
            name_parts = name.lower().split()

            if all(part in author_name for part in name_parts):
                author_id = author.get("id", "")
                institutions = [i["name"] for i in author.get("institutions", [])]

                return {
                    "found": True,
                    "author_id": author_id,
                    "author_name": author.get("name"),
                    "institutions": institutions,
                    "paper_title": work.get("title", ""),
                    "paper_id": paper_id,
                }

    return {"found": False, "message": f"未在论文中找到匹配的作者: {name}"}


def search_authors_with_works(
    name: str,
    institution_hint: str = "",
    max_candidates: int = 20,
) -> dict:
    """增强版作者搜索：同时检查作者级别和论文级别 affiliation。

    策略：
    1. 先用 search_authors 搜索作者（常规作者级别）
    2. 对候选者逐一检查其论文中的实际 affiliation
    3. 如果提供了 institution_hint，优先匹配

    适合场景：OpenAlex 作者 profile 中机构字段为空时。
    """
    r = search_authors(query=name, per_page=max_candidates)
    if r.get("error"):
        return {"error": r.get("message"), "candidates": []}

    base_candidates = r.get("results", [])
    if not base_candidates:
        return {"candidates": [], "total": 0}

    enriched = []
    for author in base_candidates:
        aid = author.get("id", "")
        aname = author.get("name", "")
        inst = author.get("institution") or ""

        enriched.append({
            "id": aid,
            "name": aname,
            "author_level_institution": inst,
            "h_index": author.get("h_index", 0),
            "works_count": author.get("works_count", 0),
            "cited_by_count": author.get("cited_by_count", 0),
            "topics": [t["name"] for t in author.get("topics", [])[:3]],
        })

    # 如果有 institution_hint，尝试从论文级数据中匹配
    # 注意：OpenAlex 作者 profile 的机构可能为空，
    # 但该作者具体论文的 authors 字段中往往包含完整机构信息
    matched = []
    hint_matched_ids = set()
    if institution_hint:
        hint_lower = institution_hint.lower()

        # 先看作者级别
        for cand in enriched:
            if hint_lower in cand["author_level_institution"].lower():
                hint_matched_ids.add(cand["id"])
                matched.append(cand)

        # 再看论文级别：对每个候选者查其论文的 authors 字段
        # search_works(author_id=...) 返回的 brief authors 字段含 institution
        for cand in enriched:
            if cand["id"] in hint_matched_ids:
                continue
            aid = cand["id"]
            paper_check = search_works(author_id=aid, per_page=20)
            if paper_check.get("error"):
                continue
            for w in paper_check.get("results", []):
                for a in w.get("authors", []):
                    if a.get("id") == aid:
                        inst = a.get("institution", "") or ""
                        if hint_lower in inst.lower():
                            cand["paper_level_institution"] = inst
                            matched.append(cand)
                            hint_matched_ids.add(aid)
                            break
                if cand["id"] in hint_matched_ids:
                    break

    return {
        "candidates": enriched,
        "matched_by_hint": matched,
        "total_candidates": len(base_candidates),
        "note": (
            f"提示机构 '{institution_hint}' 的论文级匹配: {len(matched)} 人"
            if institution_hint and matched
            else (
                f"提示机构 '{institution_hint}' 无匹配，建议遍历 candidates"
                if institution_hint
                else ""
            )
        ),
    }


def diagnose_author_profile(author_id: str) -> dict:
    """诊断作者 profile 问题：对比作者级数据 vs 论文级数据。"""

    d = get_author_detail(author_id=author_id)
    if d.get("error"):
        return {"error": d.get("message")}

    r = d.get("result", {})

    author_level_insts = [i["name"] for i in r.get("institutions_full", [])]
    author_level_inst = r.get("institution", "")

    paper_level_insts = set()
    paper_titles = []
    paper_count = 0

    w = get_author_works(author_id=author_id, per_page=20)
    if not w.get("error"):
        for p in w.get("results", []):
            paper_count += 1
            paper_titles.append(p.get("title", ""))
            for a in p.get("authors", []):
                aid = a.get("id") or ""
                if aid.endswith(author_id.split("/")[-1]):
                    inst = a.get("institution", "")
                    if inst:
                        paper_level_insts.add(inst)

    return {
        "author_id": author_id,
        "name": r.get("name", ""),
        "h_index": r.get("h_index", 0),
        "author_level_institutions": author_level_insts or [author_level_inst],
        "paper_level_institutions": sorted(paper_level_insts),
        "gap_exists": set(author_level_insts or [author_level_inst]) != paper_level_insts,
        "paper_count": paper_count,
        "paper_samples": paper_titles[:5],
        "topics": [t["name"] for t in r.get("topics", [])[:5]],
        "diagnosis": (
            "作者级机构数据为空，但论文级机构包含具体信息。"
            "应通过 search_works 而非 search_authors 来定位此人。"
            if not author_level_insts and paper_level_insts
            else "数据一致"
        ),
    }
