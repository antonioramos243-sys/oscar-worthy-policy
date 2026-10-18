"""Configuration, read from the environment. See .env.example."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    """Local working directories. Contents are gitignored."""

    policies: Path = REPO_ROOT / "data" / "policies"
    renders: Path = REPO_ROOT / "data" / "renders"

    def ensure(self) -> None:
        for p in (self.policies, self.renders):
            p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    """Runtime settings.

    Nothing here validates credentials: a missing key surfaces when the stage
    that needs it runs, so the CLI stays usable offline while stages are stubs.
    """

    gcp_project: str | None = None
    gcs_bucket: str | None = None
    region: str = "us-central1"
    llm_provider: str = "gemini"
    ig_user_id: str | None = None
    paths: Paths = field(default_factory=Paths)

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            gcp_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            gcs_bucket=os.getenv("OWP_GCS_BUCKET"),
            region=os.getenv("OWP_REGION", "us-central1"),
            llm_provider=os.getenv("OWP_LLM_PROVIDER", "gemini"),
            ig_user_id=os.getenv("IG_USER_ID"),
        )
