try:
    import requests
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests>=2.25.0"])
    import requests

from .detail import get_author_detail, get_author_works, get_work_detail
from .network import (
    build_citation_network,
    build_coauthor_network,
    get_citations,
    get_references,
    get_related_works,
)
from .search import (
    search_authors,
    search_concepts,
    search_institutions,
    search_works,
    search_works_with_expansion,
)
from .search_helpers import (
    diagnose_author_profile,
    find_author_by_paper,
    search_authors_with_works,
)

__all__ = [
    "search_works",
    "search_works_with_expansion",
    "search_authors",
    "search_institutions",
    "search_concepts",
    "get_work_detail",
    "get_author_detail",
    "get_author_works",
    "get_citations",
    "get_references",
    "get_related_works",
    "build_citation_network",
    "build_coauthor_network",
    "find_author_by_paper",
    "search_authors_with_works",
    "diagnose_author_profile",
]
