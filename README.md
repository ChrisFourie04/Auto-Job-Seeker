# 🔍 JobHunter

**Autonomous job scraping agent** that monitors job boards for software development roles, internships, and graduate programmes — then sends beautiful, relevance-scored Discord notifications for new matches.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Status: Active](https://img.shields.io/badge/status-active-success.svg)

---

## ✨ Features

- **4 Free API Sources** — Remote OK, Remotive, We Work Remotely, Jobicy (no heavy page scraping/headless browsers needed!).
- **Smart Scoring & Filtering** — Relevance scoring (0-100) based on role titles, levels, skill keywords, and positive/negative matches.
- **De-duplication** — Powered by a local SQLite cache. You will **never** receive duplicate notifications for the same job.
- **Discord Notifications** — Sends clean, color-coded rich embeds explaining *why* the job matched.
- **Automated Scheduling** — Runs locally via **Cron** or **Systemd User Timers** (no root/sudo required, runs whenever your laptop is on).
- **100% Free** — No paid developer APIs, proxies, or cloud subscriptions required.

---

## 🚀 Quick Start

### 1. Create a Discord Webhook
1. Open Discord and go to your server settings.
2. Go to **Integrations** → **Webhooks** → **New Webhook**.
3. Name it "JobHunter", choose a channel, and click **Copy Webhook URL**.

### 2. Run the Automated Installer
Run the installer script:
```bash
chmod +x setup_auto.sh
./setup_auto.sh
```

The script will:
- Set up a Python virtual environment (`.venv`) and install dependencies.
- Prompt for your Discord Webhook URL and write it to `.env`.
- Detect your system's capabilities (Cron or Systemd) and register the automated background scheduler (default: every 2 hours).
- Trigger a test scan immediately.

---

## ⚙️ How the Automated Run Works

The setup script configures either **Cron** or **Systemd User Timers** to execute the job scraper automatically.

### Systemd User Timer (Default for systemd environments)
Systemd user timers do not require root privileges. They run within your user session:
- **Service Configuration**: `~/.config/systemd/user/jobhunter.service`
- **Timer Configuration**: `~/.config/systemd/user/jobhunter.timer`

**Commands to manage the timer:**
```bash
# Check status of the timer
systemctl --user status jobhunter.timer

# View active user timers
systemctl --user list-timers

# Force run a scan immediately via systemd
systemctl --user start jobhunter.service

# View daemon logs
tail -n 50 logs/systemd.log
```

### Cron Job (Fallback)
If `cron` is used, the script installs a line in your local user crontab:
```bash
# Check if cron is running
crontab -l
```

---

## 🛠️ Admin Control Panel & CLI

We created [manage.py](file:///home/christhebot/antigravity/fearless-brahmagupta/manage.py) in the root of the project to serve as your admin dashboard. You can run it either as an interactive, menu-driven control panel (if launched without arguments) or as a direct CLI command utility.

### Interactive Menu
```bash
./manage.py
```
This launches a text-based menu to check status, edit tuning parameters (relevance threshold, Discord webhook), manage keywords (add/remove search words or exclusions), view logs, and trigger manual scans.

### Direct CLI Commands
```bash
# Check status and database stats
./manage.py status

# Run a scan right now manually
./manage.py run

# Show last 50 lines of scraper logs
./manage.py logs

# Show last 50 lines of systemd scheduler execution logs
./manage.py logs --systemd

# Print current keyword configuration (in JSON)
./manage.py keywords

# Show key environment settings
./manage.py config
```

---

## 🧠 Smart Scoring Engine

The scoring system (`jobhunter/matcher.py`) dynamically scores job listings from 0 to 100 based on your profile config:

- **Role Match (+30 pts)**: Title matches primary keywords (e.g., `software developer`, `full stack`, `AI engineer`).
- **Level Match (+20 pts)**: Title matches junior/intern/graduate keywords.
- **Skills Match (+10 pts per skill, max +30)**: Match technical skills (e.g., `python`, `javascript`, `ai`, `automation`) in title or description.
- **Location Match (+15 pts)**: Location field or title contains Cape Town, Stellenbosch, Remote, etc.
- **Tags Match (+5 pts per tag, max +15)**: API-returned tags match your skill keywords.
- **Seniority Filter (-50 pts)**: Title contains negative keywords like `senior`, `lead`, `principal`, `manager`.
- **Threshold**: Only jobs scoring $\ge$ `MIN_RELEVANCE_SCORE` (default: 30) trigger a Discord notification.

---

## ⚙️ Configuration (`.env`)

All key tunables reside in `.env`:
```ini
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SCAN_INTERVAL_HOURS=2
MIN_RELEVANCE_SCORE=30
LOG_LEVEL=INFO
```
To adjust search keywords or location targets, customize `jobhunter/config.py`.

---

## 📊 Job Sources

| Source | Method | Status | Details |
|--------|--------|--------|---------|
| [Remote OK](https://remoteok.com) | JSON API | ✅ Active | Standard remote programming listings |
| [Remotive](https://remotive.com) | JSON API | ✅ Active | Curated developer roles |
| [We Work Remotely](https://weworkremotely.com) | RSS Feed | ✅ Active | Programming RSS feed aggregator |
| [Jobicy](https://jobicy.com) | JSON API | ✅ Active | Developer remote jobs feed |
| Careers24 | HTML Scraper | 🔜 Phase 2 | Focuses on Western Cape local listings |
| Graduates24 | HTML Scraper | 🔜 Phase 2 | Focuses on SA Graduate & Internship programs |

---

## 🗂️ Project Structure

```
fearless-brahmagupta/
├── jobhunter/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Orchestrates sources -> matcher -> database -> notifier
│   ├── config.py             # Keyword definitions & environment configurations
│   ├── database.py           # SQLite manager for Seen Jobs cache
│   ├── matcher.py            # Main relevance scoring engine
│   ├── notifier.py           # Discord webhook rich embeds formatter
│   ├── utils.py              # Text truncators, HTML cleaning, rate limit utilities
│   └── sources/
│       ├── __init__.py       # Registry of active job fetcher sources
│       ├── base.py           # Standardized Job dataclass and JobSource abstract base
│       ├── remoteok.py       # Remote OK API Fetcher
│       ├── remotive.py       # Remotive API Fetcher
│       ├── weworkremotely.py  # WWR Feed Parser
│       └── jobicy.py         # Jobicy API Fetcher
├── data/jobs.db              # SQLite Database (auto-generated)
├── logs/                     # System logs directory (auto-generated)
├── .env                      # Secrets & API settings (gitignored)
├── .env.example              # Env template
├── requirements.txt          # Python packages
├── setup_auto.sh             # Auto-installer script
└── README.md                 # Project documentation
```

---

## 🔧 Extending the Agent

To add a new job board/source:
1. Create a new file under `jobhunter/sources/`.
2. Inherit from `JobSource` and override `fetch_jobs()` and `source_name`.
3. Register the class in `jobhunter/sources/__init__.py`.

---

## 📄 License

MIT License — do whatever you want with it!
