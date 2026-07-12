"""Base classes and data structures for job source fetchers."""

import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests


@dataclass
class Job:
    """Represents a single job listing."""

    id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    salary: str = ''
    tags: list[str] = field(default_factory=list)
    posted_date: str = ''
    source: str = ''


class JobSource(ABC):
    """Abstract base class for all job source fetchers.

    Provides a shared HTTP session, logging, and safe error handling
    for concrete source implementations.
    """

    def __init__(self, session: requests.Session | None = None) -> None:
        if session is not None:
            self.session = session
        else:
            self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'JobHunter/1.0 (autonomous job scraper)',
        })
        self.logger = logging.getLogger(f'jobhunter.sources.{self.source_name}')

    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        """Fetch jobs from the source. Must be implemented by subclasses."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the human-readable name of this job source."""
        ...

    def safe_fetch(self) -> list[Job]:
        """Wrap fetch_jobs in error handling, returning an empty list on failure."""
        self.logger.info(f'Fetching jobs from {self.source_name}...')
        try:
            return self.fetch_jobs()
        except Exception:
            self.logger.error(
                f'Error fetching jobs from {self.source_name}:\n{traceback.format_exc()}'
            )
            return []
