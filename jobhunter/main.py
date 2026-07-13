"""
JobHunter — Main entry point.

Orchestrates the full job scanning pipeline:
1. Fetch jobs from all enabled sources
2. Filter & score with keyword matcher
3. Check database for duplicates
4. Send Discord notifications for new matches
5. Log summary
"""

import sys
import time
import logging
import requests
from datetime import datetime

from jobhunter.config import get_config
from jobhunter.utils import setup_logging
from jobhunter.database import DatabaseManager
from jobhunter.matcher import JobMatcher
from jobhunter.notifier import DiscordNotifier
from jobhunter.sources import ALL_SOURCES


logger = logging.getLogger("jobhunter.main")


def run_scan() -> None:
    """Execute a single scan cycle across all job sources."""
    start_time = time.time()
    config = get_config()

    # --- Setup ---
    setup_logging(log_level=config.LOG_LEVEL, log_path=config.LOG_PATH)
    logger.info("=" * 60)
    logger.info("JobHunter scan started at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # Validate webhook URL
    if not config.DISCORD_WEBHOOK_URL:
        logger.error(
            "DISCORD_WEBHOOK_URL is not set! "
            "Copy .env.example to .env and add your webhook URL."
        )
        print(
            "\n❌ ERROR: DISCORD_WEBHOOK_URL is not set!\n"
            "   1. Copy .env.example to .env\n"
            "   2. Create a Discord webhook (Server Settings > Integrations > Webhooks)\n"
            "   3. Paste the URL into .env\n"
        )
        sys.exit(1)

    db = DatabaseManager(config.DB_PATH)
    matcher = JobMatcher(config)
    notifier = DiscordNotifier(config.DISCORD_WEBHOOK_URL)

    # --- Fetch from all sources ---
    all_jobs = []
    active_sources = []
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})

    for source_cls in ALL_SOURCES:
        source = source_cls(session=session)
        jobs = source.safe_fetch()
        if jobs:
            active_sources.append(source.source_name)
            all_jobs.extend(jobs)
            logger.info(
                "  ✓ %s: %d jobs fetched", source.source_name, len(jobs)
            )
        else:
            logger.warning("  ✗ %s: no jobs returned", source.source_name)

    logger.info("Total jobs fetched: %d from %d sources", len(all_jobs), len(active_sources))

    if not all_jobs:
        logger.warning("No jobs fetched from any source. Check your internet connection.")
        notifier.send_error("No jobs fetched from any source. Check internet connection or source availability.")
        return

    # --- Match & filter ---
    matched_jobs = matcher.filter_jobs(all_jobs)
    logger.info("Matched jobs above threshold: %d", len(matched_jobs))

    # --- Check for new jobs & notify ---
    new_count = 0
    for job, score, reasons in matched_jobs:
        # Use source + job ID for deduplication
        if db.is_seen(job.source, job.id):
            continue

        # New job! Send notification
        success = notifier.send_job(job, score, reasons)
        db.mark_seen(
            source=job.source,
            external_id=job.id,
            title=job.title,
            company=job.company,
            url=job.url,
            score=score,
            notified=success,
        )
        new_count += 1
        logger.info(
            "  🆕 NEW: [%d/100] %s at %s (%s)",
            score, job.title, job.company, job.source,
        )

    # --- Cleanup old entries ---
    cleaned = db.cleanup(days=30)
    if cleaned > 0:
        logger.info("Cleaned up %d old job entries", cleaned)

    # --- Send summary ---
    elapsed = time.time() - start_time
    logger.info("-" * 60)
    logger.info(
        "Scan complete: %d new matches / %d total scanned / %.1fs elapsed",
        new_count, len(all_jobs), elapsed,
    )
    logger.info("-" * 60)

    # Only send Discord summary if there were new matches
    if new_count > 0:
        notifier.send_summary(
            new_count=new_count,
            total_scanned=len(all_jobs),
            sources=active_sources,
        )

    # Print to console for manual runs
    print(f"\n✅ Scan complete!")
    print(f"   📊 Scanned: {len(all_jobs)} jobs from {len(active_sources)} sources")
    print(f"   🎯 Matched: {len(matched_jobs)} jobs above threshold")
    print(f"   🆕 New:     {new_count} new jobs sent to Discord")
    print(f"   ⏱️  Time:    {elapsed:.1f}s\n")

    # Get and display database stats
    stats = db.get_stats()
    print(f"   💾 Database: {stats['total']} total jobs tracked, {stats['today']} seen today")


def get_current_user() -> str:
    """Safely get current username."""
    import os
    import getpass
    try:
        return os.environ.get("USER") or os.environ.get("LOGNAME") or getpass.getuser()
    except Exception:
        import subprocess
        try:
            return subprocess.check_output(["whoami"], text=True).strip()
        except Exception:
            return "christhebot"


def run_loop() -> None:
    """Run the scan in a loop as long as the user's terminal is active."""
    import os
    import subprocess
    
    config = get_config()
    setup_logging(log_level=config.LOG_LEVEL, log_path=config.LOG_PATH)
    logger.info("JobHunter loop daemon started.")
    
    # Run a scan immediately on startup
    first_run = True
    
    # Calculate interval in seconds
    interval_seconds = int(config.SCAN_INTERVAL_HOURS * 3600)
    if interval_seconds <= 0:
        interval_seconds = 7200  # Default to 2 hours
        
    while True:
        if not first_run:
            # Check if any interactive terminal session (bash or zsh) is open for the current user
            username = get_current_user()
            try:
                res = subprocess.run(
                    ["pgrep", "-u", username, "-f", "(-bash|bash|-zsh|zsh)"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                if res.returncode != 0:
                    logger.info("No active terminal sessions found. JobHunter loop daemon exiting.")
                    break
            except Exception as e:
                logger.warning("Error checking active terminal sessions: %s. Continuing loop.", e)
        
        first_run = False
        
        logger.info("Starting scheduled loop scan (interval: %.1f hours)...", config.SCAN_INTERVAL_HOURS)
        try:
            run_scan()
        except Exception as e:
            logger.exception("Error during scheduled loop scan")
            
        logger.info("Loop scan finished. Sleeping for %d seconds...", interval_seconds)
        time.sleep(interval_seconds)


def main() -> None:
    """Entry point with error handling."""
    if "--loop" in sys.argv:
        try:
            run_loop()
        except KeyboardInterrupt:
            print("\n\n⛔ Loop daemon interrupted by user.")
            sys.exit(0)
        except Exception as e:
            logger.exception("Fatal error during loop run")
            sys.exit(1)
    else:
        try:
            run_scan()
        except KeyboardInterrupt:
            print("\n\n⛔ Scan interrupted by user.")
            sys.exit(0)
        except Exception as e:
            logger.exception("Fatal error during scan")
            print(f"\n❌ Fatal error: {e}")
            print("   Check logs/jobhunter.log for details.")

            # Try to send error notification
            try:
                config = get_config()
                if config.DISCORD_WEBHOOK_URL:
                    notifier = DiscordNotifier(config.DISCORD_WEBHOOK_URL)
                    notifier.send_error(f"Fatal error: {e}")
            except Exception:
                pass

            sys.exit(1)



if __name__ == "__main__":
    main()
