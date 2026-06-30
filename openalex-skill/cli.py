"""
OpenAlex 学术检索 CLI (JSON 输出)

用法:
  python cli.py search-works <query> [--limit N] [--year Y] [--sort SORT] [--expand] [--pretty]
  python cli.py search-authors <name> [--limit N] [--pretty]
  python cli.py search-institutions <name> [--limit N] [--pretty]
  python cli.py search-concepts <name> [--limit N] [--pretty]
  python cli.py work <work_id> [--pretty]
  python cli.py author <author_id> [--pretty]
  python cli.py works-of <author_id> [--limit N] [--pretty]
  python cli.py citations <work_id> [--limit N] [--pretty]
  python cli.py references <work_id> [--limit N] [--pretty]
  python cli.py related <work_id> [--limit N] [--pretty]
  python cli.py network citations <work_id> [--max-nodes N] [--direction both|backward|forward] [--depth N] [--pretty]
  python cli.py network coauthors <author_id> [--max-works N] [--pretty]

所有命令默认输出 JSON，添加 --pretty 获得带缩进的可读格式。
"""
import json
import argparse
import io
import sys
from typing import Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, __file__.rstrip("cli.py"))

from scripts import (
    search_works, search_works_with_expansion,
    search_authors, search_institutions, search_concepts,
    get_work_detail, get_author_detail, get_author_works,
    get_citations, get_references, get_related_works,
    build_citation_network, build_coauthor_network,
)


def die(msg: str, code: str = "API_ERROR"):
    output = {"status": "error", "error": {"code": code, "message": msg}}
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(1)


# ---------- JSON 输出 ----------

def print_json(data, pretty=False):
    """统一的 JSON 输出函数"""
    if isinstance(data, dict) and data.get("error"):
        err_msg = data.get("message", "")
        if not err_msg and isinstance(data["error"], str):
            err_msg = data["error"]
        output = {
            "status": "error",
            "error": {
                "code": "API_ERROR",
                "message": err_msg or "Unknown error"
            }
        }
    else:
        output = {"status": "ok", "data": data}
    indent = 2 if pretty else None
    print(json.dumps(output, ensure_ascii=False, indent=indent))


# ---------- CLI 命令 ----------

def cmd_search_works(args):
    per_page = min(args.limit, 25)
    if args.limit > per_page:
        kwargs = {"per_page": per_page, "max_results": args.limit}
    else:
        kwargs = {"per_page": per_page}
    if getattr(args, "source", None):
        kwargs["source"] = args.source
    if getattr(args, "year", None):
        kwargs["year"] = args.year
    if getattr(args, "sort", None):
        kwargs["sort"] = args.sort
    if getattr(args, "expand", False):
        r = search_works_with_expansion(query=args.query, **kwargs)
    else:
        r = search_works(query=args.query, **kwargs)
    if r.get("error"):
        die(r.get("message", "搜索失败"))
    print_json(r, args.pretty)


def cmd_search_authors(args):
    r = search_authors(query=args.name, per_page=args.limit)
    if r.get("error"):
        die(r.get("message", "搜索失败"))
    print_json(r, args.pretty)


def cmd_search_institutions(args):
    r = search_institutions(query=args.name, per_page=args.limit)
    if r.get("error"):
        die(r.get("message", "搜索失败"))
    print_json(r, args.pretty)


def cmd_search_concepts(args):
    r = search_concepts(query=args.name, per_page=args.limit)
    if r.get("error"):
        die(r.get("message", "搜索失败"))
    print_json(r, args.pretty)


def cmd_work(args):
    r = get_work_detail(args.work_id)
    if r.get("error"):
        die(r.get("message", "获取论文详情失败"))
    print_json(r["result"], args.pretty)


def cmd_author(args):
    r = get_author_detail(args.author_id)
    if r.get("error"):
        die(r.get("message", "获取作者详情失败"))
    data = r["result"]
    works = get_author_works(args.author_id, sort="cited_by_count:desc", per_page=5)
    if works.get("results"):
        data["top_works"] = works
    print_json(data, args.pretty)


def cmd_works_of(args):
    r = get_author_works(args.author_id, sort="cited_by_count:desc", per_page=args.limit)
    if r.get("error"):
        die(r.get("message", "获取作者论文失败"))
    print_json(r, args.pretty)


def cmd_citations(args):
    r = get_citations(args.work_id, per_page=min(args.limit, 25), max_results=args.limit)
    if r.get("error"):
        die(r.get("message", "获取引用失败"))
    print_json(r, args.pretty)


def cmd_references(args):
    r = get_references(args.work_id, per_page=args.limit)
    if r.get("error"):
        die(r.get("message", "获取参考文献失败"))
    print_json(r, args.pretty)


def cmd_related(args):
    r = get_related_works(args.work_id, max_results=args.limit)
    if r.get("error"):
        die(r.get("message", "获取相关论文失败"))
    print_json(r, args.pretty)


def cmd_network_citations(args):
    r = build_citation_network(
        args.work_id,
        direction=args.direction,
        depth=args.depth,
        max_nodes=args.max_nodes,
        max_requests=args.max_requests,
    )
    print_json(r, args.pretty)


def cmd_network_coauthors(args):
    r = build_coauthor_network(args.author_id, max_works=args.max_works)
    print_json(r, args.pretty)


# ---------- 入口 ----------

def main():
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    parser = argparse.ArgumentParser(
        description="OpenAlex 学术检索 CLI (JSON 输出)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        parents=[base],
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    # search-works
    p = sub.add_parser("search-works", help="搜索论文", parents=[base])
    p.add_argument("query", help="搜索关键词")
    p.add_argument("--limit", "-l", type=int, default=25, help="返回数量 (默认 25)")
    p.add_argument("--year", type=int, help="精确年份")
    p.add_argument("--sort", help='排序 (如 "cited_by_count:desc")')
    p.add_argument("--source", help='来源期刊 ID (如 "S101209419|S23254222" 多期刊用 | 分隔)')
    p.add_argument("--expand", action="store_true", help="启用同义词扩展（经济学术语）")
    p.set_defaults(func=cmd_search_works)

    # search-authors
    p = sub.add_parser("search-authors", help="搜索作者", parents=[base])
    p.add_argument("name", help="作者名")
    p.add_argument("--limit", "-l", type=int, default=25, help="返回数量 (默认 25)")
    p.set_defaults(func=cmd_search_authors)

    # search-institutions
    p = sub.add_parser("search-institutions", help="搜索机构", parents=[base])
    p.add_argument("name", help="机构名")
    p.add_argument("--limit", "-l", type=int, default=25, help="返回数量 (默认 25)")
    p.set_defaults(func=cmd_search_institutions)

    # search-concepts
    p = sub.add_parser("search-concepts", help="搜索概念", parents=[base])
    p.add_argument("name", help="概念名")
    p.add_argument("--limit", "-l", type=int, default=25, help="返回数量 (默认 25)")
    p.set_defaults(func=cmd_search_concepts)

    # work
    p = sub.add_parser("work", help="论文详情", parents=[base])
    p.add_argument("work_id", help="论文 ID (支持 OpenAlex ID / DOI)")
    p.set_defaults(func=cmd_work)

    # author
    p = sub.add_parser("author", help="作者详情 (含代表作)", parents=[base])
    p.add_argument("author_id", help="作者 ID (支持 OpenAlex ID / ORCID)")
    p.set_defaults(func=cmd_author)

    # works-of
    p = sub.add_parser("works-of", help="某作者的全部论文", parents=[base])
    p.add_argument("author_id", help="作者 ID")
    p.add_argument("--limit", "-l", type=int, default=25, help="返回数量 (默认 25)")
    p.set_defaults(func=cmd_works_of)

    # citations
    p = sub.add_parser("citations", help="施引文献", parents=[base])
    p.add_argument("work_id", help="论文 ID")
    p.add_argument("--limit", "-l", type=int, default=25, help="返回数量 (默认 25)")
    p.set_defaults(func=cmd_citations)

    # references
    p = sub.add_parser("references", help="参考文献", parents=[base])
    p.add_argument("work_id", help="论文 ID")
    p.add_argument("--limit", "-l", type=int, default=25, help="返回数量 (默认 25)")
    p.set_defaults(func=cmd_references)

    # related
    p = sub.add_parser("related", help="相关论文", parents=[base])
    p.add_argument("work_id", help="论文 ID")
    p.add_argument("--limit", "-l", type=int, default=10, help="返回数量 (默认 10)")
    p.set_defaults(func=cmd_related)

    # network citations / coauthors
    p = sub.add_parser("network", help="引用网络 / 合著者网络 [子命令: citations|coauthors]", parents=[base])
    net_sub = p.add_subparsers(dest="network_type")
    net_sub.required = True

    pn = net_sub.add_parser("citations", help="引用网络", parents=[base])
    pn.add_argument("work_id", help="论文 ID")
    pn.add_argument("--max-nodes", type=int, default=50, help="最大节点数 (默认 50)")
    pn.add_argument("--max-requests", type=int, default=15, help="最大 API 调用次数 (默认 15)")
    pn.add_argument("--depth", type=int, default=1, choices=[1, 2], help="追溯深度 (默认 1)")
    pn.add_argument("--direction", default="both", choices=["forward", "backward", "both"], help="引用方向 (默认 both)")
    pn.set_defaults(func=cmd_network_citations)

    pn = net_sub.add_parser("coauthors", help="合著者网络", parents=[base])
    pn.add_argument("author_id", help="作者 ID")
    pn.add_argument("--max-works", type=int, default=50, help="分析论文数 (默认 50)")
    pn.set_defaults(func=cmd_network_coauthors)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
