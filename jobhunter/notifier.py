import time
import logging
from datetime import datetime

from discord_webhook import DiscordWebhook, DiscordEmbed

from jobhunter.sources.base import Job
from jobhunter.utils import truncate


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

            embed.add_embed_field(name="🏢 Company", value=job.company, inline=True)
            embed.add_embed_field(name="📍 Location", value=job.location, inline=True)
            embed.add_embed_field(
                name="🎯 Score", value=f"{score:.0f}/100", inline=True
            )

            if job.salary:
                embed.add_embed_field(name="💰 Salary", value=job.salary, inline=True)

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
