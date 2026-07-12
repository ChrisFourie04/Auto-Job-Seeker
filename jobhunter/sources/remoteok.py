"""Job source fetcher for Remote OK (remoteok.com)."""

from jobhunter.sources.base import Job, JobSource
from jobhunter.utils import clean_html


class RemoteOKSource(JobSource):
    """Fetches remote job listings from the Remote OK API.

    Remote OK provides a JSON API at https://remoteok.com/api.
    The first element in the response array is a legal notice and is skipped.
    """

    @property
    def source_name(self) -> str:
        return 'Remote OK'

    def fetch_jobs(self) -> list[Job]:
        """Fetch jobs from the Remote OK API."""
        response = self.session.get(
            'https://remoteok.com/api',
            headers={'Accept': 'application/json'},
            timeout=30,
        )
        response.raise_for_status()

        # First element is a legal notice — skip it
        data = response.json()[1:]

        jobs: list[Job] = []
        for item in data:
            slug = item.get('slug', item.get('id', ''))
            url = f'https://remoteok.com/remote-jobs/{slug}'

            salary_min = item.get('salary_min', '')
            salary_max = item.get('salary_max', '')
            if salary_min and salary_max:
                salary = f'${salary_min} - ${salary_max}'
            elif salary_min:
                salary = f'${salary_min}'
            elif salary_max:
                salary = f'${salary_max}'
            else:
                salary = ''

            job = Job(
                id=str(item.get('id', '')),
                title=item.get('position', ''),
                company=item.get('company', ''),
                location=item.get('location', 'Remote'),
                url=url,
                description=clean_html(item.get('description', '')),
                salary=salary,
                tags=item.get('tags', []),
                posted_date=item.get('date', ''),
                source='Remote OK',
            )
            jobs.append(job)

        self.logger.info(f'Fetched {len(jobs)} jobs from {self.source_name}')
        return jobs
