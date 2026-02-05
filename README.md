# bot-parser

This project scrapes apartment listings from ss.com and posts them to a Telegram bot.

Setup

1. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright browsers (required by the map scraper):

```bash
python -m playwright install
```

4. Set up environment/config (`config.py`) with your `BOT_TOKEN` and `DATABASE_URL`.

5. Run the bot:

```bash
python bot.py
```

Notes

- The map scraper uses Playwright (headless) to obtain session cookies and then requests to the map endpoint. Keep Playwright installed and browsers installed via `playwright install`.
- If you add or remove dependencies, update `requirements.txt` and reinstall.
