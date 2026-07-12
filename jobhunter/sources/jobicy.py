"""Job source fetcher for Jobicy (jobicy.com)."""

from jobhunter.sources.base import Job, JobSource
from jobhunter.utils import clean_html


class JobicySource(JobSource):
    """Fetches remote job listings from the Jobicy API.

    Jobicy provides a JSON API for remote developer jobs
    at https://jobicy.com/api/v2/remote-jobs.
    """

    @property
    def source_name(self) -> str:
        return 'Jobicy'

    def fetch_jobs(self) -> list[Job]:
        """Fetch jobs from the Jobicy API."""
        response = self.session.get(
            'https://jobicy.com/api/v2/remote-jobs',
            params={'count': '50', 'industry': 'dev'},
            timeout=30,
        )
        response.raise_for_status()

        data = response.json().get('jobs', [])

        jobs: list[Job] = []
        for item in data:
            salary_min = item.get('annualSalaryMin', '')
            salary_max = item.get('annualSalaryMax', '')
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
                title=item.get('jobTitle', ''),
                company=item.get('companyName', ''),
                location=item.get('jobGeo', 'Remote'),
                url=item.get('url', ''),
                description=clean_html(item.get('jobDescription', '')),
                salary=salary,
                tags=[],
                posted_date=item.get('pubDate', ''),
                source='Jobicy',
            )
            jobs.append(job)

        self.logger.info(f'Fetched {len(jobs)} jobs from {self.source_name}')
        return jobs
