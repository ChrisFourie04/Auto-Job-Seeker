"""Job source fetcher for LinkedIn guest search API."""

import re
import hashlib
from bs4 import BeautifulSoup
from jobhunter.sources.base import Job, JobSource


class LinkedInSource(JobSource):
    """Fetches job listings from LinkedIn's public guest search API.

    Bypasses authentication limits using the public Guest search endpoints.
    """

    @property
    def source_name(self) -> str:
        return 'LinkedIn'

    def fetch_jobs(self) -> list[Job]:
        """Fetch software developer and tech jobs from LinkedIn South Africa."""
        # Query broad search terms to loosen the filters a bit
        search_terms = ['software developer', 'software engineer', 'intern software']
        jobs: list[Job] = []

        for term in search_terms:
            url = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
            params = {
                'keywords': term,
                'location': 'South Africa',
                'start': 0
            }
            try:
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    self.logger.warning(
                        f"Failed to fetch LinkedIn search for '{term}': HTTP {response.status_code}"
                    )
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.find_all('li')

                for card in cards:
                    title_elem = card.find(class_=re.compile('search-card__title|card__title'))
                    company_elem = card.find(
                        class_=re.compile('search-card__subtitle|card__subtitle|hidden-nested-link')
                    )
                    loc_elem = card.find(class_=re.compile('search-card__location|card__location'))
                    link_elem = card.find('a', class_=re.compile('card__full-link|full-link'))
                    time_elem = card.find('time')

                    if not title_elem or not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                    location = loc_elem.get_text(strip=True) if loc_elem else 'South Africa'
                    
                    # Clean LinkedIn guest search URLs
                    job_url = link_elem['href'].split('?')[0]

                    # Extract LinkedIn numeric job ID or generate one
                    job_id = None
                    id_match = re.search(r'-(\d+)$', job_url)
                    if id_match:
                        job_id = id_match.group(1)
                    else:
                        job_id = hashlib.md5(job_url.encode()).hexdigest()

                    date_str = time_elem.get('datetime', '') if time_elem else ''

                    # Place a summary description since fetching full description for every card
                    # would make separate requests and cause rapid rate-limiting
                    desc = f"Software developer position at {company} in {location} listed on LinkedIn."

                    job = Job(
                        id=f'linkedin-{job_id}',
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        description=desc,
                        posted_date=date_str,
                        source=self.source_name,
                    )
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error fetching LinkedIn for term '{term}': {e}")

        self.logger.info(f'Fetched {len(jobs)} jobs from LinkedIn')
        return jobs
