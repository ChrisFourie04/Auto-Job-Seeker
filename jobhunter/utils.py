"""Utility helpers for JobHunter — logging, rate-limiting, text cleaning."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path


# ── Logging ───────────────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"


def setup_logging(
    log_level: str = "INFO",
    log_path: Path | None = None,
) -> logging.Logger:
    """Configure root logger with console + optional file handlers.

    Args:
        log_level: Logging level name (DEBUG, INFO, WARNING, ERROR).
        log_path: If provided, logs will also be written to this file.
                  Parent directories are created automatically.

    Returns:
        The root logger.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid duplicate handlers on repeated calls
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # File handler (optional)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


# ── Rate Limiter ──────────────────────────────────────────────────────────────


class RateLimiter:
    """Simple per-key rate limiter that enforces a minimum delay between calls."""

    def __init__(self) -> None:
        self._last_call: dict[str, float] = {}

    def wait(self, key: str, min_delay: float = 1.0) -> None:
        """Sleep if necessary to enforce *min_delay* seconds since the last call for *key*.

        Args:
            key: Identifier for the source being rate-limited.
            min_delay: Minimum seconds between consecutive calls for this key.
        """
        now = time.monotonic()
        last = self._last_call.get(key)
        if last is not None:
            elapsed = now - last
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)
        self._last_call[key] = time.monotonic()


# ── Text Helpers ──────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace.

    Args:
        text: Raw HTML or mixed content string.

    Returns:
        Plain text with tags removed and whitespace normalised.
    """
    stripped = _HTML_TAG_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", stripped).strip()


def truncate(text: str, max_length: int = 200) -> str:
    """Truncate *text* to *max_length* characters, appending '...' if trimmed.

    Args:
        text: The string to truncate.
        max_length: Maximum allowed length (including the ellipsis).

    Returns:
        The original string if short enough, otherwise a truncated version.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
