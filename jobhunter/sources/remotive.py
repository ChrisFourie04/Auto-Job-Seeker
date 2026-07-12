"""Job source fetcher for Remotive (remotive.com)."""

from jobhunter.sources.base import Job, JobSource
from jobhunter.utils import clean_html


class RemotiveSource(JobSource):
    """Fetches remote job listings from the Remotive API.

    Remotive provides a JSON API for remote software development jobs
    at https://remotive.com/api/remote-jobs.
    """

    @property
    def source_name(self) -> str:
        return 'Remotive'

    def fetch_jobs(self) -> list[Job]:
        """Fetch jobs from the Remotive API."""
        response = self.session.get(
            'https://remotive.com/api/remote-jobs',
            params={'category': 'software-dev', 'limit': '50'},
            timeout=30,
        )
        response.raise_for_status()

        data = response.json().get('jobs', [])

        jobs: list[Job] = []
        for item in data:
            job = Job(
                id=str(item.get('id', '')),
                title=item.get('title', ''),
                company=item.get('company_name', ''),
                location=item.get('candidate_required_location', 'Remote'),
                url=item.get('url', ''),
                description=clean_html(item.get('description', '')),
                salary=item.get('salary', ''),
                tags=item.get('tags', []),
                posted_date=item.get('publication_date', ''),
                source='Remotive',
            )
            jobs.append(job)

        self.logger.info(f'Fetched {len(jobs)} jobs from {self.source_name}')
        return jobs
