import logging
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


def scrape_description(url: str) -> str:
    logger = logging.getLogger(__name__)
    logger.info("Fetching card description: %s", url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")

        desc = soup.select_one("#msg_div_msg")
        return desc.text.strip() if desc else ""
    except Exception:
        logger.exception("Failed to fetch description for %s", url)
        return ""
