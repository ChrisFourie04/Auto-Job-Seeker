import logging

from jobhunter.sources.base import Job
from jobhunter.config import Config


class JobMatcher:
    """Scores and filters jobs based on keyword relevance matching."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def score_job(self, job: Job) -> tuple[float, list[str]]:
        """Score a job based on keyword matching. Returns (score, reasons)."""
        score = 0
        reasons = []

        title_lower = job.title.lower() if job.title else ""
        description_lower = job.description.lower() if job.description else ""

        # Primary role keywords in title (+30)
        for keyword in self.config.KEYWORDS_PRIMARY:
            if keyword.lower() in title_lower:
                score += 30
                reasons.append(f"Role: {keyword}")
                break

        # Level keywords in title (+20)
        for keyword in self.config.KEYWORDS_LEVEL:
            if keyword.lower() in title_lower:
                score += 20
                reasons.append(f"Level: {keyword}")
                break

        # Skills keywords in title or description (+10 each, cap at 30)
        skills_score = 0
        for keyword in self.config.KEYWORDS_SKILLS:
            if skills_score >= 30:
                break
            keyword_lower = keyword.lower()
            if keyword_lower in title_lower or keyword_lower in description_lower:
                skills_score += 10
                reasons.append(f"Skill: {keyword}")
        score += skills_score

        # Location matching (+15)
        location_lower = job.location.lower() if job.location else ""
        location_matched = False
        for location in self.config.LOCATIONS_POSITIVE:
            if location.lower() in location_lower:
                score += 15
                reasons.append(f"Location: {location}")
                location_matched = True
                break
        if not location_matched and "remote" in title_lower:
            score += 15
            reasons.append("Location: remote")

        # Tag matching (+5 each, cap at 15)
        tags_score = 0
        if job.tags:
            skills_lower = {k.lower() for k in self.config.KEYWORDS_SKILLS}
            for tag in job.tags:
                if tags_score >= 15:
                    break
                if tag.lower() in skills_lower:
                    tags_score += 5
                    reasons.append(f"Tag: {tag}")
        score += tags_score

        # Negative keywords (-50)
        for keyword in self.config.KEYWORDS_NEGATIVE:
            if keyword.lower() in title_lower:
                score -= 50
                reasons.append(f"Negative: {keyword}")
                break

        # Clamp to 0-100
        score = max(0, min(100, score))

        return (score, reasons)

    def filter_jobs(self, jobs: list[Job]) -> list[tuple[Job, float, list[str]]]:
        """Score and filter jobs, keeping those above the minimum relevance score."""
        results = []
        for job in jobs:
            score, reasons = self.score_job(job)
            if score >= self.config.MIN_RELEVANCE_SCORE:
                results.append((job, score, reasons))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        self.logger.info(
            "%d of %d jobs matched (min score: %s)",
            len(results),
            len(jobs),
            self.config.MIN_RELEVANCE_SCORE,
        )

        return results
