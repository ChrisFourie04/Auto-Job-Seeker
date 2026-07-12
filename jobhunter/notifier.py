import re
import time
import logging
from datetime import datetime

from discord_webhook import DiscordWebhook, DiscordEmbed

from jobhunter.sources.base import Job
from jobhunter.utils import truncate


def format_salary_zar(salary_str: str) -> str:
    """Parse and convert foreign salary values to South African Rands (ZAR).

    Maintains the original currency in parentheses for clarity.
    Approximate rates: USD=18.0, EUR=19.5, GBP=23.0
    """
    if not salary_str:
        return ""

    s = salary_str.lower().strip()

    # Identify currency & set target ZAR rate
    rate = 1.0
    original_currency = ""

    if "$" in s or "usd" in s:
        rate = 18.0
        original_currency = "USD"
    elif "€" in s or "eur" in s:
        rate = 19.5
        original_currency = "EUR"
    elif "£" in s or "gbp" in s:
        rate = 23.0
        original_currency = "GBP"
    elif "r" in s or "zar" in s:
        # Already in South African Rands
        return salary_str

    if not original_currency:
        # Unknown/Unmatched currency format
        return salary_str

    # Helper to convert "80k" -> 80000.0 or "100,000" -> 100000.0
    def clean_number_str(num_str: str) -> float:
        num_str = num_str.replace("k", "000")
        digits = re.sub(r"[^\d]", "", num_str)
        return float(digits) if digits else 0.0

    # Extract sequences of numbers (e.g. 50,000 or 50k)
    parts = re.findall(r"\d+(?:\s*\d+)*(?:\s*k)?", s)
    if not parts:
        return salary_str

    try:
        converted_parts = []
        for part in parts:
            val = clean_number_str(part)
            if val > 0:
                zar_val = val * rate
                # Format ZAR nicely with thousands separator
                converted_parts.append(f"R{zar_val:,.0f}")

        if len(converted_parts) == 1:
            return f"{converted_parts[0]} (originally {salary_str})"
        elif len(converted_parts) >= 2:
            return f"{converted_parts[0]} - {converted_parts[1]} (originally {salary_str})"
    except Exception:
        pass

    return salary_str


class DiscordNotifier:
    """Sends job notifications to Discord via webhook."""

    def __init__(self, webhook_url: str):
        if not webhook_url:
            raise ValueError("Discord webhook URL must not be empty")
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)

    def _color_for_score(self, score: float) -> str:
        """Return a hex color string based on the relevance score."""
        if score >= 70:
            return "2ecc71"
        elif score >= 50:
            return "f39c12"
        else:
            return "3498db"

    def send_job(self, job: Job, score: float, reasons: list[str]) -> bool:
        """Send a single job notification to Discord. Returns True on success."""
        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            embed = DiscordEmbed(
                title=job.title,
                url=job.url,
                color=self._color_for_score(score),
            )

            embed.set_description(truncate(job.description, 200))

            # Include location info in the company field as requested
            company_value = f"{job.company} ({job.location})" if job.location else job.company
            embed.add_embed_field(name="🏢 Company", value=company_value, inline=True)
            embed.add_embed_field(name="📍 Location", value=job.location, inline=True)
            embed.add_embed_field(
                name="🎯 Score", value=f"{score:.0f}/100", inline=True
            )

            if job.salary:
                zar_salary = format_salary_zar(job.salary)
                embed.add_embed_field(name="💰 Salary", value=zar_salary, inline=True)

            if job.tags:
                embed.add_embed_field(
                    name="🏷️ Tags", value=", ".join(job.tags[:5]), inline=False
                )

            matched_reasons = "\n".join(f"• {r}" for r in reasons)
            embed.add_embed_field(
                name="✨ Why matched", value=matched_reasons, inline=False
            )

            embed.set_footer(text=f"Source: {job.source}")

            webhook.add_embed(embed)
            webhook.execute()

            time.sleep(0.5)  # Rate limiting
            return True
        except Exception as e:
            self.logger.error("Failed to send job notification: %s", e)
            return False

    def send_summary(
        self, new_count: int, total_scanned: int, sources: list[str]
    ) -> bool:
        """Send a scan summary notification. Returns True on success."""
        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            embed = DiscordEmbed(
                title="📊 JobHunter Scan Complete",
                color="2c3e50",
            )

            embed.add_embed_field(
                name="🆕 New Matches", value=str(new_count), inline=True
            )
            embed.add_embed_field(
                name="🔍 Total Scanned", value=str(total_scanned), inline=True
            )
            embed.add_embed_field(
                name="📡 Sources", value=", ".join(sources), inline=False
            )
            embed.add_embed_field(
                name="⏰ Timestamp",
                value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                inline=False,
            )

            webhook.add_embed(embed)
            webhook.execute()
            return True
        except Exception as e:
            self.logger.error("Failed to send summary notification: %s", e)
            return False

    def send_error(self, error_msg: str) -> bool:
        """Send an error notification to Discord. Returns True on success."""
        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            embed = DiscordEmbed(
                title="❌ JobHunter Error",
                description=error_msg,
                color="e74c3c",
            )

            webhook.add_embed(embed)
            webhook.execute()
            return True
        except Exception as e:
            self.logger.error("Failed to send error notification: %s", e)
            return False
