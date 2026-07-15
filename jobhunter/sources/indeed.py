"""Job source fetcher for Indeed South Africa (za.indeed.com) scraping HTML pages."""

import re
import hashlib
from curl_cffi import requests
from bs4 import BeautifulSoup

from jobhunter.sources.base import Job, JobSource
from jobhunter.utils import clean_html


class IndeedSource(JobSource):
    """Fetches job listings from Indeed za search pages.

    Bypasses Cloudflare restrictions by impersonating a Safari browser using curl_cffi.
    """

    @property
    def source_name(self) -> str:
        return 'Indeed'

    def fetch_jobs(self) -> list[Job]:
        """Fetch software/tech jobs from Indeed South Africa search pages."""
        # Loosen filters by querying multiple broad search terms
        search_terms = ['software developer', 'software engineer', 'intern software', 'graduate developer']
        jobs: list[Job] = []

        for term in search_terms:
            # We query the indeed SA search endpoint
            query = term.replace(' ', '+')
            url = f'https://za.indeed.com/jobs?q={query}&l=South+Africa&sort=date'
            try:
                # Use curl_cffi to impersonate Safari 15.5 TLS handshakes (unblocked by Indeed's Cloudflare config)
                response = requests.get(url, impersonate='safari15_5', timeout=15)
                
                if response.status_code != 200:
                    self.logger.warning(
                        f"Failed to fetch Indeed search for '{term}': HTTP {response.status_code}"
                    )
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.find_all(class_=re.compile('job_seen_beacon'))

                for card in cards:
                    # Find parent item containing metadata and snippet
                    parent = card.find_parent('li') or card.find_parent(class_=re.compile('result|cardOutline'))

                    # Title
                    title_elem = card.find(class_='jobTitle')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    # Extract cleaner title if there's a child span
                    if title_elem.find('a') and title_elem.find('a').find('span'):
                        title = title_elem.find('a').find('span').get_text(strip=True)

                    # Extract job key (data-jk)
                    link_elem = title_elem.find('a')
                    jk = None
                    if link_elem and link_elem.has_attr('data-jk'):
                        jk = link_elem['data-jk']
                    
                    if not jk:
                        continue

                    # Direct job URL
                    job_url = f'https://za.indeed.com/viewjob?jk={jk}'

                    # Company Name
                    comp_elem = card.find(attrs={'data-testid': 'company-name'})
                    company = comp_elem.get_text(strip=True) if comp_elem else 'Unknown'

                    # Location
                    loc_elem = card.find(attrs={'data-testid': 'text-location'})
                    location = loc_elem.get_text(strip=True) if loc_elem else 'South Africa'

                    # Description snippet
                    desc = ''
                    if parent:
                        desc_elem = parent.find(class_=re.compile('slider_sub_item|job-snippet|underCard'))
                        if desc_elem:
                            desc = desc_elem.get_text(separator=' ', strip=True)

                    # Salary
                    sal_elem = card.find(class_=re.compile('salary-snippet-container|metadataContainer'))
                    salary = sal_elem.get_text(strip=True) if sal_elem else ''

                    job = Job(
                        id=f'indeed-{jk}',
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        description=clean_html(desc),
                        salary=salary,
                        posted_date='', # dates on search pages can be dynamic, matcher works fine without it
                        source=self.source_name,
                    )
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error fetching Indeed page for term '{term}': {e}")

        self.logger.info(f'Fetched {len(jobs)} jobs from Indeed')
        return jobs
