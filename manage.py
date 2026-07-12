#!/usr/bin/env python3
"""JobHunter Admin CLI Control Panel.

Allows status inspection, keyword tuning, configuration management, manual scans,
and log checking directly from the terminal.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Automatically re-execute inside virtual environment if available
project_root = Path(__file__).resolve().parent
venv_python = project_root / ".venv" / "bin" / "python"
if venv_python.exists() and sys.executable != str(venv_python):
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

# Adjust path to find the jobhunter package
sys.path.insert(0, str(project_root))

from jobhunter.config import get_config, get_project_root, Config
from jobhunter.database import DatabaseManager

# Text styling colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
NC = "\033[0m"


def print_header(title: str) -> None:
    """Print a styled section header."""
    print(f"\n{CYAN}{BOLD}══ {title} ════════════════════════════════════════{NC}")


def show_status() -> None:
    """Show service, configuration, and database status."""
    print_header("JobHunter Status")
    
    # 1. Database check
    config = get_config()
    db = DatabaseManager(config.DB_PATH)
    try:
        stats = db.get_stats()
        print(f"💾 {BOLD}Database Connection:{NC} {GREEN}OK{NC}")
        print(f"   • Total Jobs Tracked: {stats['total']}")
        print(f"   • Seen Today:         {stats['today']}")
        print(f"   • Notified:           {stats['notified']}")
        print(f"   • Sources breakdown:  " + ", ".join(f"{k}: {v}" for k, v in stats['sources'].items()))
    except Exception as e:
        print(f"💾 {BOLD}Database Connection:{NC} {RED}ERROR ({e}){NC}")

    # 2. Config info
    print(f"\n⚙️ {BOLD}Settings config:{NC}")
    print(f"   • Min Relevance Score: {config.MIN_RELEVANCE_SCORE}/100")
    print(f"   • Discord Webhook:     {GREEN}Configured{NC}" if config.DISCORD_WEBHOOK_URL else f"   • Discord Webhook:     {RED}Not Configured{NC}")
    print(f"   • Database File:       {config.DB_PATH}")
    print(f"   • Logs File:           {config.LOG_PATH}")

    # 3. Systemd timer check
    print(f"\n⏱️  {BOLD}Scheduler Status (systemd user timer):{NC}")
    try:
        res = subprocess.run(
            ["systemctl", "--user", "status", "jobhunter.timer"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if "Active: active" in res.stdout:
            print(f"   • Timer status: {GREEN}Active & Enabled{NC}")
            # Find next trigger
            next_run = "Unknown"
            for line in res.stdout.split("\n"):
                if "Trigger:" in line or "Triggers:" in line:
                    next_run = line.strip()
            print(f"   • {next_run}")
        else:
            print(f"   • Timer status: {RED}Inactive / Not running{NC}")
            print(f"     Run: './setup_auto.sh' to re-register.")
    except Exception:
        print(f"   • Timer status: Unknown (systemd status check failed)")


def get_custom_keywords_path() -> Path:
    """Return path to data/config.json."""
    return get_project_root() / "data" / "config.json"


def read_custom_keywords() -> dict:
    """Read data/config.json keyword definitions."""
    path = get_custom_keywords_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Fallback/Default template structure
    cfg = get_config()
    return {
        "keywords_primary": cfg.KEYWORDS_PRIMARY,
        "keywords_skills": cfg.KEYWORDS_SKILLS,
        "keywords_level": cfg.KEYWORDS_LEVEL,
        "keywords_negative": cfg.KEYWORDS_NEGATIVE,
        "locations_positive": cfg.LOCATIONS_POSITIVE
    }


def write_custom_keywords(data: dict) -> None:
    """Write back to data/config.json."""
    path = get_custom_keywords_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"{GREEN}✓ Custom keywords successfully saved to {path}{NC}")


def manage_keywords_menu() -> None:
    """Interactive CLI menu to manage keywords."""
    while True:
        print_header("Keyword & Tuning Management")
        data = read_custom_keywords()
        
        categories = {
            "1": ("Primary Search Titles (KEYWORDS_PRIMARY)", "keywords_primary"),
            "2": ("Skill Keywords Boost (KEYWORDS_SKILLS)", "keywords_skills"),
            "3": ("Experience Level Filters (KEYWORDS_LEVEL)", "keywords_level"),
            "4": ("Exclusions / Seniors Filters (KEYWORDS_NEGATIVE)", "keywords_negative"),
            "5": ("Locations Whitelist (LOCATIONS_POSITIVE)", "locations_positive")
        }
        
        for key, (label, _) in categories.items():
            count = len(data.get(categories[key][1], []))
            print(f"   {BOLD}{key}){NC} {label} ({count} items)")
        print(f"   {BOLD}6){NC} Go Back")

        choice = input(f"\nSelect a list to edit [1-6]: ").strip()
        if choice == "6" or not choice:
            break

        if choice in categories:
            label, field_name = categories[choice]
            edit_list(data, field_name, label)


def edit_list(data: dict, field_name: str, label: str) -> None:
    """Helper to display, add, or remove elements from a specific keyword category."""
    while True:
        print_header(f"Editing: {label}")
        items = data.get(field_name, [])
        
        # Display current items
        for i, item in enumerate(sorted(items)):
            print(f"   • {item}")
        
        print(f"\nOptions:  {BOLD}a{NC} (Add item) | {BOLD}r{NC} (Remove item) | {BOLD}b{NC} (Back)")
        opt = input("Choice: ").strip().lower()
        
        if opt == "b" or not opt:
            break
        elif opt == "a":
            new_val = input("Enter new keyword/phrase: ").strip().lower()
            if new_val and new_val not in items:
                items.append(new_val)
                data[field_name] = items
                write_custom_keywords(data)
        elif opt == "r":
            rem_val = input("Enter keyword/phrase to remove: ").strip().lower()
            if rem_val in items:
                items.remove(rem_val)
                data[field_name] = items
                write_custom_keywords(data)
            else:
                print(f"{RED}Word '{rem_val}' not found in the list.{NC}")


def edit_env_settings() -> None:
    """Modify environment configuration settings."""
    print_header("Tuning Environment Settings")
    env_path = get_project_root() / ".env"
    
    if not env_path.exists():
        print(f"{RED}Error: .env file does not exist. Run setup_auto.sh first.{NC}")
        return
        
    config = get_config()
    print(f"   1) Minimum relevance score threshold (currently: {config.MIN_RELEVANCE_SCORE})")
    print(f"   2) Log Level (currently: {config.LOG_LEVEL})")
    print(f"   3) Discord Webhook URL (currently: {'Set' if config.DISCORD_WEBHOOK_URL else 'Empty'})")
    print(f"   4) Go Back")

    choice = input("\nSelect setting to edit [1-4]: ").strip()
    if choice == "4" or not choice:
        return

    # Helper to update key in .env file
    def update_env(key: str, val: str):
        lines = env_path.read_text(encoding="utf-8").splitlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={val}"
                updated = True
                break
        if not updated:
            lines.append(f"{key}={val}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{GREEN}✓ Updated {key} to {val} in .env file.{NC}")

    if choice == "1":
        new_score = input("Enter new minimum relevance score (0-100): ").strip()
        if new_score.isdigit():
            update_env("MIN_RELEVANCE_SCORE", new_score)
    elif choice == "2":
        new_level = input("Enter log level (DEBUG/INFO/WARNING/ERROR): ").strip().upper()
        if new_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            update_env("LOG_LEVEL", new_level)
    elif choice == "3":
        new_url = input("Enter new Discord Webhook URL: ").strip()
        if new_url:
            update_env("DISCORD_WEBHOOK_URL", new_url)


def run_scan_now() -> None:
    """Manually run a scan cycle."""
    print_header("Running JobHunter Scan Now")
    try:
        from jobhunter.main import main as run_pipeline
        run_pipeline()
    except Exception as e:
        print(f"\n{RED}Error running scan: {e}{NC}")


def view_logs(tail_count: int = 50, show_systemd: bool = False) -> None:
    """View detailed logs."""
    config = get_config()
    log_file = config.LOG_PATH
    if show_systemd:
        log_file = get_project_root() / "logs" / "systemd.log"
        print_header(f"Showing last {tail_count} lines of systemd.log")
    else:
        print_header(f"Showing last {tail_count} lines of jobhunter.log")
        
    if not log_file.exists():
        print(f"{YELLOW}Log file {log_file} does not exist yet. Run a scan first.{NC}")
        return

    try:
        lines = log_file.read_text(encoding="utf-8").splitlines()
        for line in lines[-tail_count:]:
            # Highlight errors
            if "ERROR" in line:
                print(f"{RED}{line}{NC}")
            elif "WARNING" in line:
                print(f"{YELLOW}{line}{NC}")
            elif "🆕 NEW" in line or "✓" in line:
                print(f"{GREEN}{line}{NC}")
            else:
                print(line)
    except Exception as e:
        print(f"{RED}Error reading logs: {e}{NC}")


def interactive_menu() -> None:
    """Run the main interactive menu loop."""
    while True:
        print(f"\n{CYAN}{BOLD}╔═══════════════════════════════════════════════════╗{NC}")
        print(f"{CYAN}{BOLD}║         ⚙️  JobHunter Admin Control Panel           ║{NC}")
        print(f"{CYAN}{BOLD}╚═══════════════════════════════════════════════════╝{NC}")
        print("   1) Show Status & Database stats")
        print("   2) Configure Tuning Settings (.env)")
        print("   3) Manage Search Keywords & Locations (config.json)")
        print("   4) Run Scan Now (Manual run)")
        print("   5) View Scraper Logs")
        print("   6) View Systemd Daemon execution logs")
        print("   7) Exit")

        choice = input(f"\nSelect option [1-7]: ").strip()
        if choice == "7":
            print(f"{GREEN}Goodbye! Keep hunting.{NC}")
            sys.exit(0)
        
        if choice == "1":
            show_status()
        elif choice == "2":
            edit_env_settings()
        elif choice == "3":
            manage_keywords_menu()
        elif choice == "4":
            run_scan_now()
        elif choice == "5":
            view_logs()
        elif choice == "6":
            view_logs(show_systemd=True)
        else:
            print(f"{RED}Invalid selection!{NC}")
        
        input(f"\nPress Enter to continue...")


def main() -> None:
    """CLI Entrypoint processing arguments or displaying interactive menu."""
    parser = argparse.ArgumentParser(description="JobHunter Admin utility CLI")
    parser.add_argument("command", nargs="?", help="Action to run: status, config, keywords, run, logs")
    parser.add_argument("--tail", type=int, default=50, help="Number of log lines to show (default: 50)")
    parser.add_argument("--systemd", action="store_true", help="Show systemd runner logs instead of scraper logs")

    args = parser.parse_args()

    if not args.command:
        # Fall back to interactive control panel if no args given
        try:
            interactive_menu()
        except KeyboardInterrupt:
            print(f"\n{GREEN}Goodbye!{NC}")
            sys.exit(0)
    else:
        cmd = args.command.lower()
        if cmd == "status":
            show_status()
        elif cmd == "run":
            run_scan_now()
        elif cmd == "logs":
            view_logs(args.tail, args.systemd)
        elif cmd == "keywords":
            # Command line display of keywords
            data = read_custom_keywords()
            print(json.dumps(data, indent=2))
        elif cmd == "config":
            # Command line display of config
            cfg = get_config()
            print(f"MIN_RELEVANCE_SCORE: {cfg.MIN_RELEVANCE_SCORE}")
            print(f"LOG_LEVEL: {cfg.LOG_LEVEL}")
            print(f"DISCORD_WEBHOOK_URL: {cfg.DISCORD_WEBHOOK_URL}")
        else:
            print(f"Unknown command '{cmd}'. Available: status, run, logs, keywords, config")


if __name__ == "__main__":
    main()
