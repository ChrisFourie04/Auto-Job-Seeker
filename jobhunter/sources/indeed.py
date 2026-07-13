"""Job source fetcher for Indeed South Africa (za.indeed.com) RSS feeds."""

import urllib.parse
import hashlib
import feedparser
from jobhunter.sources.base import Job, JobSource
from jobhunter.utils import clean_html


class IndeedSource(JobSource):
    """Fetches job listings from Indeed za RSS feeds.

    Bypasses Cloudflare restrictions by pulling XML feeds rather than full page HTML.
    """

    @property
    def source_name(self) -> str:
        return 'Indeed'

    def fetch_jobs(self) -> list[Job]:
        """Fetch software/tech jobs from Indeed South Africa RSS feeds."""
        # Loosen filters a bit by checking multiple broad search terms
        search_terms = ['software developer', 'intern software', 'graduate developer']
        jobs: list[Job] = []

        for term in search_terms:
            # URL-encode the search query to prevent control character errors
            term_encoded = urllib.parse.quote(term)
            url = f'https://za.indeed.com/rss?q={term_encoded}&l=South+Africa'
            try:
                feed = feedparser.parse(url)
                
                # Check for errors in parsing
                if feed.bozo:
                    self.logger.warning(
                        f"Indeed RSS feed parser warning for '{term}': {feed.bozo_exception}"
                    )

                for entry in feed.entries:
                    title = entry.get('title', '')
                    company = 'Unknown'
                    location = 'South Africa'

                    # Indeed RSS titles format: "Job Title - Company - Location"
                    parts = title.split(' - ')
                    if len(parts) >= 3:
                        title = parts[0]
                        company = parts[1]
                        location = parts[2]
                    elif len(parts) == 2:
                        title = parts[0]
                        company = parts[1]

                    job_url = entry.get('link', '')
                    if not job_url:
                        continue

                    job_id = hashlib.md5(job_url.encode()).hexdigest()
                    desc = clean_html(entry.get('summary', ''))

                    # Extract salary if available
                    salary = ''
                    if 'salary' in entry:
                        salary = entry.get('salary', '')

                    job = Job(
                        id=f'indeed-{job_id}',
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        description=desc,
                        salary=salary,
                        posted_date=entry.get('published', ''),
                        source=self.source_name,
                    )
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error fetching Indeed RSS for term '{term}': {e}")

        self.logger.info(f'Fetched {len(jobs)} jobs from Indeed')
        return jobs
