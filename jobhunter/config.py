"""Central configuration module for JobHunter.

Loads settings from environment variables (via .env) and custom keywords from
data/config.json if available.
"""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env file at module level so env vars are available immediately
load_dotenv()


def get_project_root() -> Path:
    """Return the project root directory (parent of the jobhunter package)."""
    return Path(__file__).resolve().parent.parent


@dataclass
class Config:
    """Application-wide configuration."""

    # ── Primary job-title keywords ────────────────────────────────────
    KEYWORDS_PRIMARY: list[str] = field(default_factory=lambda: [
        "software developer",
        "software engineer",
        "full stack developer",
        "fullstack developer",
        "frontend developer",
        "backend developer",
        "web developer",
        "python developer",
        "javascript developer",
        "AI engineer",
        "machine learning engineer",
        "data scientist",
        "database administrator",
        "devops engineer",
    ])

    # ── Skill keywords ────────────────────────────────────────────────
    KEYWORDS_SKILLS: list[str] = field(default_factory=lambda: [
        "python",
        "javascript",
        "typescript",
        "react",
        "node",
        "sql",
        "ai",
        "machine learning",
        "automation",
        "django",
        "flask",
        "fastapi",
        "docker",
    ])

    # ── Entry-level / junior keywords ─────────────────────────────────
    KEYWORDS_LEVEL: list[str] = field(default_factory=lambda: [
        "junior",
        "entry level",
        "entry-level",
        "intern",
        "internship",
        "graduate",
        "graduate programme",
        "learnership",
        "trainee",
        "associate",
    ])

    # ── Negative (senior-level) filters ───────────────────────────────
    KEYWORDS_NEGATIVE: list[str] = field(default_factory=lambda: [
        "senior",
        "lead",
        "principal",
        "staff",
        "director",
        "manager",
        "head of",
        "10+ years",
        "8+ years",
        "7+ years",
        "vp of",
    ])

    # ── Location filters ──────────────────────────────────────────────
    LOCATIONS_POSITIVE: list[str] = field(default_factory=lambda: [
        "remote",
        "anywhere",
        "worldwide",
        "cape town",
        "stellenbosch",
        "western cape",
        "south africa",
        "paarl",
        "somerset west",
    ])

    LOCATIONS_NEGATIVE: list[str] = field(default_factory=list)

    # ── Tunables (loaded from environment) ────────────────────────────
    MIN_RELEVANCE_SCORE: int = 20
    DISCORD_WEBHOOK_URL: str = ""
    LOG_LEVEL: str = "INFO"

    # ── Paths ─────────────────────────────────────────────────────────
    DB_PATH: Path = field(default_factory=lambda: get_project_root() / "data" / "jobs.db")
    LOG_PATH: Path = field(default_factory=lambda: get_project_root() / "logs" / "jobhunter.log")

    # ── HTTP ──────────────────────────────────────────────────────────
    USER_AGENT: str = "JobHunter/1.0 (autonomous job scraper)"

    def load_custom_config(self) -> None:
        """Load overrides from data/config.json if they exist."""
        custom_path = get_project_root() / "data" / "config.json"
        if custom_path.exists():
            try:
                with open(custom_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Load keywords if present
                if "keywords_primary" in data:
                    self.KEYWORDS_PRIMARY = data["keywords_primary"]
                if "keywords_skills" in data:
                    self.KEYWORDS_SKILLS = data["keywords_skills"]
                if "keywords_level" in data:
                    self.KEYWORDS_LEVEL = data["keywords_level"]
                if "keywords_negative" in data:
                    self.KEYWORDS_NEGATIVE = data["keywords_negative"]
                if "locations_positive" in data:
                    self.LOCATIONS_POSITIVE = data["locations_positive"]
            except Exception:
                # Fail silently or fall back to defaults
                pass


def get_config() -> Config:
    """Create a Config instance populated from environment variables and JSON."""
    cfg = Config(
        MIN_RELEVANCE_SCORE=int(os.getenv("MIN_RELEVANCE_SCORE", "30")),
        DISCORD_WEBHOOK_URL=os.getenv("DISCORD_WEBHOOK_URL", ""),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
    )
    cfg.load_custom_config()
    return cfg
