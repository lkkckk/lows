"""
Search engine client (OpenSearch/Elasticsearch) using HTTP API.
"""
from typing import Any, Dict, Optional
import os
import httpx

_SEARCH_ENGINE = None


class SearchEngine:
    def __init__(
        self,
        base_url: str,
        index: str,
        username: Optional[str],
        password: Optional[str],
        verify_ssl: bool,
        timeout: float,
    ):
        self.base_url = base_url.rstrip("/")
        self.index = index
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    @classmethod
    def from_env(cls) -> "SearchEngine":
        base_url = (
            os.getenv("SEARCH_ENGINE_URL")
            or os.getenv("OPENSEARCH_URL")
            or os.getenv("ELASTICSEARCH_URL")
            or ""
        )
        index = os.getenv("SEARCH_ENGINE_INDEX", "law_articles")
        username = os.getenv("SEARCH_ENGINE_USER")
        password = os.getenv("SEARCH_ENGINE_PASSWORD")
        verify_ssl = os.getenv("SEARCH_ENGINE_VERIFY_SSL", "true").lower() != "false"
        timeout = float(os.getenv("SEARCH_ENGINE_TIMEOUT", "10"))
        return cls(base_url, index, username, password, verify_ssl, timeout)

    async def search_articles(
        self, query: str, page: int, page_size: int
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        offset = max(page - 1, 0) * page_size
        payload = {
            "from": offset,
            "size": page_size,
            "track_total_hits": True,
            "query": {
                "function_score": {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "content^4",
                                "keywords^3",
                                "article_display^2",
                                "law_title^2",
                            ],
                            "type": "best_fields",
                            "operator": "and",
                        }
                    },
                    "field_value_factor": {
                        "field": "law_weight",
                        "factor": 0.1,
                        "missing": 0,
                    },
                    "boost_mode": "sum",
                }
            },
            "sort": ["_score", {"article_num": "asc"}],
            "highlight": {
                "fields": {
                    "content": {"fragment_size": 120, "number_of_fragments": 1},
                    "article_display": {"fragment_size": 120, "number_of_fragments": 1},
                }
            },
        }

        auth = None
        if self.username and self.password:
            auth = (self.username, self.password)

        url = f"{self.base_url}/{self.index}/_search"
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=self.timeout) as client:
            response = await client.post(url, json=payload, auth=auth)
            response.raise_for_status()

        data = response.json()
        total = data.get("hits", {}).get("total", {})
        total_value = total.get("value", total) if isinstance(total, dict) else total
        hits = data.get("hits", {}).get("hits", [])

        results = []
        for hit in hits:
            source = hit.get("_source", {})
            highlight = ""
            hl = hit.get("highlight") or {}
            if hl.get("content"):
                highlight = " ... ".join(hl["content"])
            elif hl.get("article_display"):
                highlight = " ... ".join(hl["article_display"])

            results.append({
                "law_id": source.get("law_id"),
                "law_title": source.get("law_title", ""),
                "law_category": source.get("law_category", ""),
                "article_num": source.get("article_num"),
                "article_display": source.get("article_display", ""),
                "content": source.get("content", ""),
                "highlight": highlight or source.get("content", "")[:120],
                "score": hit.get("_score"),
            })

        total_pages = (total_value + page_size - 1) // page_size if total_value else 0
        return {
            "data": results,
            "pagination": {
                "total": total_value or 0,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        }


def get_search_engine() -> SearchEngine:
    global _SEARCH_ENGINE
    if _SEARCH_ENGINE is None:
        _SEARCH_ENGINE = SearchEngine.from_env()
    return _SEARCH_ENGINE
