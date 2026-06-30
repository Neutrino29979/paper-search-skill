import time

import requests

from .config import BASE_URL, CACHE_TTL, MAILTO, MAX_PAGINATION, MAX_RETRIES, RETRY_DELAY, TIMEOUT

_cache = {}
_WORK_SELECT = "id,title,publication_year,cited_by_count,authorships,primary_location,type,doi,language,open_access,concepts,abstract_inverted_index"
_AUTHOR_SELECT = "id,display_name,orcid,works_count,cited_by_count,summary_stats,last_known_institutions,x_concepts,topics"


def _cache_key(endpoint: str, params: dict) -> tuple:
    clean = {k: v for k, v in (params or {}).items() if k != "mailto"}
    return (endpoint, tuple(sorted(clean.items())))


def request(endpoint: str, params: dict = None) -> dict:
    if params is None:
        params = {}

    key = _cache_key(endpoint, params)
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["time"] < CACHE_TTL:
            return entry["data"]

    if MAILTO:
        params["mailto"] = MAILTO

    url = BASE_URL + endpoint

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            result = resp.json()
            if "error" not in result:
                _cache[key] = {"data": result, "time": time.time()}
            return result
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 404:
                return {"error": True, "message": f"资源不存在 (404): {endpoint}", "results": []}
            if resp.status_code == 429:
                wait = RETRY_DELAY * (attempt + 2) * 2
                time.sleep(wait)
                continue
            return {"error": True, "message": f"HTTP错误 {resp.status_code}: {str(e)}", "results": []}
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return {"error": True, "message": "请求超时，请稍后重试", "results": []}
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return {"error": True, "message": f"网络错误: {str(e)}", "results": []}

    return {"error": True, "message": "请求失败，已达最大重试次数", "results": []}


def paginate(endpoint: str, params: dict, max_results: int = MAX_PAGINATION) -> dict:
    all_results = []
    params = params.copy() if params else {}
    params["cursor"] = "*"

    while len(all_results) < max_results:
        data = request(endpoint, params)
        if data.get("error"):
            return data

        meta = data.get("meta", {})
        batch = data.get("results", [])
        if not batch:
            break

        all_results.extend(batch)
        next_cursor = meta.get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor

    return {"results": all_results[:max_results], "total": len(all_results[:max_results])}


def batch_get_works(work_ids: list, select: str = None) -> list:
    if not work_ids:
        return []

    from .extractors import extract_work_brief

    all_results = []
    chunk_size = 50
    use_select = select or _WORK_SELECT

    for i in range(0, len(work_ids), chunk_size):
        chunk = work_ids[i:i + chunk_size]
        oa_ids = []
        for wid in chunk:
            wid = wid.strip()
            if wid.startswith("https://openalex.org/"):
                oa_ids.append(wid.replace("https://openalex.org/", ""))
            else:
                oa_ids.append(wid)

        if not oa_ids:
            continue

        params = {"filter": "openalex:" + "|".join(oa_ids), "per_page": len(oa_ids), "select": use_select}
        data = request("/works", params)
        if data.get("error"):
            continue

        for w in data.get("results", []):
            all_results.append(extract_work_brief(w))

    return all_results


def batch_get_authors(author_ids: list, select: str = None) -> dict:
    if not author_ids:
        return {}

    from .extractors import extract_author_brief

    result_map = {}
    chunk_size = 50
    use_select = select or _AUTHOR_SELECT

    for i in range(0, len(author_ids), chunk_size):
        chunk = author_ids[i:i + chunk_size]
        oa_ids = []
        for aid in chunk:
            aid = aid.strip()
            if aid.startswith("https://openalex.org/"):
                oa_ids.append(aid.replace("https://openalex.org/", ""))
            else:
                oa_ids.append(aid)

        if not oa_ids:
            continue

        params = {"filter": "openalex:" + "|".join(oa_ids), "per_page": len(oa_ids), "select": use_select}
        data = request("/authors", params)
        if data.get("error"):
            continue

        for a in data.get("results", []):
            aid = a.get("id", "")
            if aid:
                result_map[aid] = extract_author_brief(a)

    return result_map
