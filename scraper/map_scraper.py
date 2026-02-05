import html
import json
import re
import requests
import logging
from json import JSONDecodeError
from playwright.sync_api import sync_playwright
from shapely.geometry import Point, shape

from scraper.types import ApartmentDTO


class SsMapScraper:
    def __init__(self):
        logging.getLogger(__name__).info("Initializing SsMapScraper, loading bad regions and cookies")
        self.url = (
            "https://www.ss.com/ru/fTgTeF4QAzt4FD4eFFM=.html?map=17020&map2=17020&cat=14195&mode=3"
        )
        self.cookies_url = (
            "https://www.ss.com/ru/real-estate/flats/riga/all/fDgQeF4S.html"
        )

        try:
            with open("bad_regions.geojson") as f:
                geojson = json.load(f)

            self.bad_regions = [
                shape(feature["geometry"]) for feature in geojson["features"]
            ]
            logging.getLogger(__name__).info(
                "Loaded %d bad regions from bad_regions.geojson", len(self.bad_regions)
            )
        except FileNotFoundError:
            # If the geojson isn't present, don't fail - treat as no bad regions.
            self.bad_regions = []
            logging.getLogger(__name__).info("bad_regions.geojson not found, continuing without exclusions")

        self.cookies = self._get_cookies()

    def _get_cookies(self):
        logging.getLogger(__name__).info("Retrieving cookies via Playwright")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(self.cookies_url)
            cookies = context.cookies()
            page.close()
            browser.close()
            logging.getLogger(__name__).debug("Playwright returned %d cookies", len(cookies))
            # find PHPSESSID cookie safely
            for c in cookies:
                if c.get("name") == "PHPSESSID":
                    logging.getLogger(__name__).info("Found PHPSESSID cookie")
                    return {"PHPSESSID": c.get("value")}

            logging.getLogger(__name__).warning("PHPSESSID cookie not found; requests may be unauthenticated")
            return {}

    def scrape(self) -> list[ApartmentDTO]:
        logging.getLogger(__name__).info("Requesting map data URL %s", self.url)
        response = requests.get(self.url, cookies=self.cookies)
        match = re.search(
            r"var\s+MARKER_DATA\s*=\s*(\[.*?\]);",
            response.text,
            re.S,
        )

        if not match:
            return []

        raw = match.group(1)
        try:
            marker_data = json.loads(raw)
        except JSONDecodeError:
            try:
                fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)
                marker_data = json.loads(fixed)
            except Exception:
                logging.getLogger(__name__).exception(
                    "Failed to decode MARKER_DATA JSON; skipping map scrape"
                )
                return []
        flats: list[ApartmentDTO] = []

        for raw in marker_data:
            elements = [
                html.unescape(x)
                .replace("<b>", "")
                .replace("</b>", "")
                for x in raw.split("<br>")
            ]

            if len(elements) < 7:
                continue

            lat, lon, *_ = elements[0].split("|")
            address = elements[1]
            # parse numeric fields safely; skip entry on parse errors
            try:
                rooms = int(elements[2].split(" ")[1])

                floor_raw = elements[4].split(" ")[1].split("/")
                # floor_raw may contain '-' or other non-numeric markers
                floor = int(floor_raw[0])
                total_floors = int(floor_raw[1])

                price = int(elements[6].split(" ")[1].replace(",", ""))
            except (ValueError, IndexError) as e:
                logging.getLogger(__name__).debug(
                    "Skipping flat due to parse error: %s; elements=%s", e, elements
                )
                continue

            if not self._valid_neighbourhood(lat, lon):
                logging.getLogger(__name__).debug("Flat at %s,%s excluded by bad regions", lat, lon)
                continue

            url = self._build_url(elements)

            flats.append(
                ApartmentDTO(
                    external_id=url,
                    lat=float(lat),
                    lon=float(lon),
                    address=address,
                    price=price,
                    rooms=rooms,
                    floor=floor,
                    total_floors=total_floors,
                    url=url,
                )
            )

        logging.getLogger(__name__).info("Scrape complete, returning %d valid flats", len(flats))
        return flats

    def _valid_neighbourhood(self, lat: str, lon: str) -> bool:
        point = Point(float(lon), float(lat))
        return not any(p.contains(point) for p in self.bad_regions)

    def _build_url(self, elements: list[str]) -> str:
        for el in elements:
            # Try to extract href="..." robustly
            m = re.search(r'href\s*=\s*"([^"]+)"', el)
            if m:
                return "https://www.ss.com" + m.group(1)
            # Fallback: original brittle parse
            if "href=" in el:
                parts = el.split('"')
                if len(parts) > 1:
                    return "https://www.ss.com" + parts[1]
        return ""
