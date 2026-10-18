"""Component 1: acquiring the 40 target policies."""

from owp.acquisition.base import ExtractionFailed, PolicyFetcher, TargetSource
from owp.acquisition.curated import CuratedTargetSource
from owp.acquisition.http_fetcher import HttpPolicyFetcher, content_hash, merge_documents
from owp.acquisition.manual import corpus_from_text
from owp.acquisition.store import corpus_path, load_corpus, save_corpus

__all__ = [
    "CuratedTargetSource",
    "ExtractionFailed",
    "HttpPolicyFetcher",
    "PolicyFetcher",
    "TargetSource",
    "content_hash",
    "corpus_from_text",
    "corpus_path",
    "load_corpus",
    "merge_documents",
    "save_corpus",
]
