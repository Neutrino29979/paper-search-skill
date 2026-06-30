# API 参考文档

## 分页规则

| 场景 | 写法 | 返回 |
|------|------|------|
| 默认 | `search_works(query=...)` | 25 篇（第 1 页） |
| 指定页 | `search_works(query=..., per_page=10, page=2)` | 第 2 页 10 篇 |
| 自动翻页 | `search_works(query=..., max_results=100)` | 自动取满 100 篇 |

**AI 原则**：先读 `total` 字段判断是否够用，不够则设 `max_results`。

## 搜索排序策略

| 场景 | sort 参数 |
|------|-----------|
| 找相关度最高的 | `relevance`（默认） |
| 找高引经典 | `cited_by_count:desc` |
| 找最新研究 | `publication_year:desc` |
| 找最早文献 | `publication_year:asc` |

## 函数签名

### search_works(query, year, year_from, year_to, author_id, institution_id, concept_id, sort, per_page, page, max_results, min_citations, open_access, type_filter, select)

标准论文搜索，支持多条件过滤。

- `query`: str — 搜索关键词
- `year`: int — 精确年份
- `year_from` / `year_to`: int — 年份范围
- `author_id`: str — 作者 ID（支持 Axxx / OpenAlex URL / ORCID）
- `institution_id`: str — 机构 ID
- `concept_id`: str — 概念 ID
- `sort`: str — 排序方式
- `per_page`: int — 每页数量（默认 25，最大 200）
- `page`: int — 页码（默认 1）
- `max_results`: int — 自动翻页取满数量（设置后 page 参数被忽略）
- `min_citations`: int — 最低被引量
- `open_access`: bool — 是否仅开放获取
- `type_filter`: str — 论文类型过滤
- `select`: list — 限制返回字段（如 `["id","title","cited_by_count"]`），减少响应体 60-80%

**返回：** `{"results": [...], "total": N, "per_page": N, "page": N}`

### search_works_with_expansion(query, llm_synonyms, always_expand, **kwargs)

带同义词扩展的论文搜索。默认策略：原始查询结果不足时自动用同义词重试。

- `query`: str — 搜索关键词
- `llm_synonyms`: list — LLM 动态生成的额外同义词
- `always_expand`: bool — 始终用所有同义词展开合并（默认 False）

**返回：** `{"results": [...], "total": N, "expansions_used": [...], "note": "..."}`

### search_authors(query, institution_id, concept_id, per_page, page, min_works, min_citations, select)

搜索学者。**返回 results 中每项包含：** id, name, institution, h_index, i10_index, works_count, cited_by_count, concepts[], topics[]

- `select`: list — 限制返回字段

### search_institutions(query, country_code, type_filter, per_page, page, select)

搜索机构。**返回 results 中每项包含：** id, name, country, city, type, works_count, cited_by_count

- `select`: list — 限制返回字段

### search_concepts(query, level, per_page, page, select)

搜索学术概念/主题。**返回 results 中每项包含：** id, name, level, description, works_count, cited_by_count

- `select`: list — 限制返回字段

### get_work_detail(work_id, select)

获取单篇论文的完整详细信息。**返回 result 中包含：** 同 search_works 格式 + authors_full[], locations[], concepts[], referenced_works[], related_works[], 完整摘要

- `select`: list — 限制返回字段（不传时返回全部）

### get_author_detail(author_id, select)

获取学者的详细学术画像。**返回 result 中包含：** 同 search_authors 格式 + institutions_full[], counts_by_year[]

- `select`: list — 限制返回字段（不传时返回全部）

### get_author_works(author_id, sort, per_page, page, select)

获取某学者的论文列表。**返回：** `{"results": [...], "total": N}`

- `select`: list — 限制返回字段

### get_citations(work_id, per_page, page, max_results, select)

获取施引文献——谁引用了这篇论文。**返回：** `{"results": [...], "total": N}`

- `select`: list — 限制返回字段

### get_references(work_id, per_page, page)

获取参考文献——这篇论文引用了谁。**返回：** `{"results": [...], "total": N}`

### get_related_works(work_id, max_results)

获取算法推荐的相关论文。**返回：** `{"results": [...], "total": N}`

### build_citation_network(work_id, direction, depth, max_nodes, max_requests)

构建引用网络图。**返回：** `{"nodes": [...], "edges": [...], "summary": {...}}`

- direction: "forward" | "backward" | "both"（默认 "both"）
- depth: 1 | 2（默认 1）
- max_requests: int — 限制内部 API 调用次数（防止 depth=2 时请求过多，可选）
- summary 新增 `api_calls_made` 字段记录实际调用次数

### build_coauthor_network(author_id, max_works)

构建合著者网络图。**返回：** `{"nodes": [...], "edges": [...], "summary": {...}}`

## 返回值结构

### 论文项（search_works / get_citations / get_references / get_related_works results 中每项）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | OpenAlex ID |
| title | str | 论文标题 |
| publication_year | int | 发表年份 |
| cited_by_count | int | 被引次数 |
| authors | list | 前5作者（每项含 name, id, institution） |
| abstract | str | 摘要（截断至300字） |
| source | str | 期刊/来源 |
| type | str | 论文类型 |
| doi | str | DOI |
| language | str | 语言 |
| open_access | bool | 是否开放获取 |
| concepts | list | 前5概念（每项含 name, score） |

### 作者项（search_authors / get_author_detail results 中每项）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | OpenAlex ID |
| name | str | 姓名 |
| orcid | str | ORCID |
| works_count | int | 论文总数 |
| cited_by_count | int | 总被引 |
| h_index | int | h 指数 |
| i10_index | int | i10 指数 |
| 2yr_mean_citedness | float | 近2年平均被引 |
| institution | str | 所属机构 |
| institution_id | str | 机构 ID |
| concepts | list | 研究概念 |
| topics | list | 研究主题（含 subfield/field/domain） |

### 网络数据（build_citation_network / build_coauthor_network）

结构化 `{nodes, edges, summary}` 格式，可直接用于前端可视化或文字总结。

- `nodes`: `[{id, title, year, cited_by_count, authors, type}, ...]`
- `edges`: `[{source, target, type}, ...]`
- `summary`: `{total_nodes, total_edges, ...}`

## ID 格式支持

| 格式 | 示例 | 支持的函数 |
|------|------|-----------|
| OpenAlex ID | `W3178354421` | search_works, get_work_detail, get_citations, get_references, build_citation_network |
| OpenAlex URL | `https://openalex.org/W3178354421` | 同上 |
| DOI | `10.1257/aer.20180321` | get_work_detail |
| DOI URL | `https://doi.org/10.1257/aer.20180321` | get_work_detail |
| PMID | `pmid:12345678` | get_work_detail |
| OpenAlex Author ID | `A123456789` | search_authors, get_author_detail, get_author_works, build_coauthor_network |
| ORCID | `0000-0002-1234-5678` | get_author_detail |
| ORCID URL | `https://orcid.org/0000-0002-1234-5678` | get_author_detail |
