import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_description(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")

    desc = soup.select_one("#msg_div_msg")
    return desc.text.strip() if desc else ""
