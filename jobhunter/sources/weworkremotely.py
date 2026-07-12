"""Job source fetcher for We Work Remotely (weworkremotely.com)."""

import hashlib

import feedparser

from jobhunter.sources.base import Job, JobSource
from jobhunter.utils import clean_html


class WeWorkRemotelySource(JobSource):
    """Fetches remote job listings from the We Work Remotely RSS feed.

    We Work Remotely publishes job listings via RSS at
    https://weworkremotely.com/categories/remote-programming-jobs.rss.
    """

    @property
    def source_name(self) -> str:
        return 'We Work Remotely'

    def fetch_jobs(self) -> list[Job]:
        """Fetch jobs from the We Work Remotely RSS feed."""
        feed = feedparser.parse(
            'https://weworkremotely.com/categories/remote-programming-jobs.rss'
        )

        jobs: list[Job] = []
        for entry in feed.entries:
            raw_title = entry.get('title', '')
            # Title format is typically 'Company: Job Title'
            if ': ' in raw_title:
                company, title = raw_title.split(': ', 1)
            else:
                company = 'Unknown'
                title = raw_title

            link = entry.get('link', '')
            job_id = hashlib.md5(link.encode()).hexdigest()

            job = Job(
                id=job_id,
                title=title,
                company=company,
                location='Remote',
                url=link,
                description=clean_html(entry.get('summary', '')),
                salary='',
                tags=[],
                posted_date=entry.get('published', ''),
                source='We Work Remotely',
            )
            jobs.append(job)

        self.logger.info(f'Fetched {len(jobs)} jobs from {self.source_name}')
        return jobs
