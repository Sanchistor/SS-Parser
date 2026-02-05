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
        except FileNotFoundError:
            # If the geojson isn't present, don't fail - treat as no bad regions.
            self.bad_regions = []

        self.cookies = self._get_cookies()

    def _get_cookies(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(self.cookies_url)
            cookies = context.cookies()
            page.close()
            browser.close()
            # find PHPSESSID cookie safely
            for c in cookies:
                if c.get("name") == "PHPSESSID":
                    return {"PHPSESSID": c.get("value")}
            
            return {}

    def scrape(self) -> list[ApartmentDTO]:
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
            rooms = int(elements[2].split(" ")[1])

            floor_raw = elements[4].split(" ")[1].split("/")
            floor = int(floor_raw[0])
            total_floors = int(floor_raw[1])

            price = int(elements[6].split(" ")[1].replace(",", ""))

            if not self._valid_neighbourhood(lat, lon):
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

        return flats

    def _valid_neighbourhood(self, lat: str, lon: str) -> bool:
        point = Point(float(lon), float(lat))
        return not any(p.contains(point) for p in self.bad_regions)

    def _build_url(self, elements: list[str]) -> str:
        for el in elements:
            if "href=" in el:
                return "https://www.ss.com" + el.split('"')[1]
        return ""
