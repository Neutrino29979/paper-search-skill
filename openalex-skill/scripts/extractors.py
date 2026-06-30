from .utils import _reconstruct_abstract


def extract_work_brief(work: dict) -> dict:
    if not work:
        return {}

    abstract_idx = work.get("abstract_inverted_index")
    abstract = _reconstruct_abstract(abstract_idx)
    if abstract and len(abstract) > 300:
        abstract = abstract[:300] + "..."

    authorships = work.get("authorships") or []
    authors_brief = []
    for a in authorships[:5]:
        author_info = a.get("author") or {}
        inst_list = a.get("institutions") or []
        inst_name = inst_list[0].get("display_name", "") if inst_list else ""
        authors_brief.append({
            "name": author_info.get("display_name", ""),
            "id": author_info.get("id", ""),
            "institution": inst_name,
        })

    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}

    concepts = work.get("concepts") or []
    top_concepts = [
        {"name": c.get("display_name", ""), "score": c.get("score", 0)}
        for c in concepts[:5]
    ]

    return {
        "id": work.get("id", ""),
        "title": work.get("title", ""),
        "publication_year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count", 0),
        "authors": authors_brief,
        "abstract": abstract or "摘要不可用",
        "source": source.get("display_name", ""),
        "type": work.get("type", ""),
        "doi": work.get("doi", ""),
        "language": work.get("language", ""),
        "open_access": (work.get("open_access") or {}).get("is_oa", False),
        "concepts": top_concepts,
    }


def extract_author_brief(author: dict) -> dict:
    if not author:
        return {}

    institutions = author.get("last_known_institutions") or []
    inst_name = institutions[0].get("display_name", "") if institutions else ""
    inst_id = institutions[0].get("id", "") if institutions else ""
    summary_stats = author.get("summary_stats") or {}

    concepts = author.get("x_concepts") or []
    topics_raw = author.get("topics") or []
    top_topics = [
        {
            "name": t.get("display_name", ""),
            "subfield": (t.get("subfield") or {}).get("display_name", ""),
            "field": (t.get("field") or {}).get("display_name", ""),
            "domain": (t.get("domain") or {}).get("display_name", ""),
        }
        for t in topics_raw[:5]
    ]
    top_concepts = [
        {"name": c.get("display_name", ""), "score": c.get("score", 0)}
        for c in concepts[:5]
    ]

    return {
        "id": author.get("id", ""),
        "name": author.get("display_name", ""),
        "orcid": author.get("orcid", ""),
        "works_count": author.get("works_count", 0),
        "cited_by_count": author.get("cited_by_count", 0),
        "h_index": summary_stats.get("h_index", 0),
        "i10_index": summary_stats.get("i10_index", 0),
        "2yr_mean_citedness": summary_stats.get("2yr_mean_citedness", 0),
        "institution": inst_name,
        "institution_id": inst_id,
        "concepts": top_concepts,
        "topics": top_topics,
    }


def extract_institution_brief(inst: dict) -> dict:
    if not inst:
        return {}

    geo = inst.get("geo") or {}

    return {
        "id": inst.get("id", ""),
        "name": inst.get("display_name", ""),
        "country_code": geo.get("country_code", ""),
        "country": geo.get("country", ""),
        "city": geo.get("city", ""),
        "type": inst.get("type", ""),
        "works_count": inst.get("works_count", 0),
        "cited_by_count": inst.get("cited_by_count", 0),
        "h_index": (inst.get("summary_stats") or {}).get("h_index", 0),
        "image_url": inst.get("image_url", ""),
        "image_thumbnail_url": inst.get("image_thumbnail_url", ""),
    }
