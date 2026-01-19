"""
Reindex MongoDB law articles into OpenSearch/Elasticsearch.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict

import httpx
from pymongo import MongoClient

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app.services.law_service import get_law_weight  # noqa: E402


def get_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value is not None else default


def build_mappings(analyzer: str) -> Dict:
    return {
        "mappings": {
            "properties": {
                "law_id": {"type": "keyword"},
                "law_title": {"type": "text", "analyzer": analyzer},
                "law_category": {"type": "keyword"},
                "article_num": {"type": "integer"},
                "article_display": {"type": "text", "analyzer": analyzer},
                "content": {"type": "text", "analyzer": analyzer},
                "keywords": {"type": "text", "analyzer": analyzer},
                "law_weight": {"type": "integer"},
            }
        }
    }


def main() -> int:
    base_url = (
        get_env("SEARCH_ENGINE_URL")
        or get_env("OPENSEARCH_URL")
        or get_env("ELASTICSEARCH_URL")
    )
    if not base_url:
        print("Missing SEARCH_ENGINE_URL/OPENSEARCH_URL/ELASTICSEARCH_URL")
        return 1

    index = get_env("SEARCH_ENGINE_INDEX", "law_articles")
    analyzer = get_env("SEARCH_ENGINE_ANALYZER", "ik_smart")
    username = get_env("SEARCH_ENGINE_USER") or None
    password = get_env("SEARCH_ENGINE_PASSWORD") or None
    verify_ssl = get_env("SEARCH_ENGINE_VERIFY_SSL", "true").lower() != "false"
    batch_size = int(get_env("SEARCH_ENGINE_BATCH_SIZE", "1000"))
    recreate = "--recreate" in sys.argv

    mongo_url = get_env("MONGODB_URL", "mongodb://localhost:27017")
    mongo_db = get_env("MONGODB_DB", "law_system")

    auth = (username, password) if username and password else None
    base_url = base_url.rstrip("/")

    with httpx.Client(verify=verify_ssl, timeout=30.0, auth=auth) as client:
        if recreate:
            client.delete(f"{base_url}/{index}")

        exists = client.head(f"{base_url}/{index}").status_code == 200
        if not exists:
            resp = client.put(f"{base_url}/{index}", json=build_mappings(analyzer))
            if resp.status_code >= 400 and analyzer != "standard":
                print("Analyzer not available, fallback to standard")
                resp = client.put(f"{base_url}/{index}", json=build_mappings("standard"))
            resp.raise_for_status()

    mongo = MongoClient(mongo_url)
    db = mongo[mongo_db]
    laws = {
        law["law_id"]: {
            "title": law.get("title", ""),
            "category": law.get("category", ""),
        }
        for law in db.laws.find({}, {"law_id": 1, "title": 1, "category": 1})
    }

    cursor = db.law_articles.find({})
    bulk_lines = []
    count = 0

    def flush(lines):
        if not lines:
            return
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        with httpx.Client(verify=verify_ssl, timeout=60.0, auth=auth) as client:
            resp = client.post(
                f"{base_url}/_bulk",
                content=payload,
                headers={"Content-Type": "application/x-ndjson"},
            )
            resp.raise_for_status()

    for article in cursor:
        law_id = article.get("law_id")
        law_info = laws.get(law_id, {})
        title = law_info.get("title", "")
        doc = {
            "law_id": law_id,
            "law_title": title,
            "law_category": law_info.get("category", ""),
            "article_num": article.get("article_num"),
            "article_display": article.get("article_display", ""),
            "content": article.get("content", ""),
            "keywords": article.get("keywords", []),
            "law_weight": get_law_weight(title),
        }

        doc_id = f"{law_id}_{article.get('article_num')}"
        bulk_lines.append(json.dumps({"index": {"_index": index, "_id": doc_id}}, ensure_ascii=False))
        bulk_lines.append(json.dumps(doc, ensure_ascii=False))
        count += 1

        if count % batch_size == 0:
            flush(bulk_lines)
            bulk_lines = []
            print(f"Indexed {count} documents...")

    flush(bulk_lines)
    print(f"Indexed {count} documents total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
