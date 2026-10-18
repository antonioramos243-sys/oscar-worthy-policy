"""Component 1: acquiring the 40 target policies."""

from owp.acquisition.base import PolicyFetcher, TargetSource
from owp.acquisition.curated import CuratedTargetSource
from owp.acquisition.http_fetcher import HttpPolicyFetcher

__all__ = ["PolicyFetcher", "TargetSource", "CuratedTargetSource", "HttpPolicyFetcher"]
