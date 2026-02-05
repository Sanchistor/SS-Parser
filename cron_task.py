import asyncio
from scraper.map_scraper import SsMapScraper
from scraper.card_scraper import scrape_description
from db import Session
from models import Apartment
from utils import calc_distance
from filters import user_filters
from sqlalchemy import select

FOUR_HOURS = 4 * 60 * 60

scraper = SsMapScraper()


async def cron_parser():
    while True:
        # run the blocking scrape in a thread
        flats = await asyncio.to_thread(scraper.scrape)

        async with Session() as session:
            for flat in flats:
                exists = await session.execute(
                    select(Apartment).where(
                        Apartment.external_id == flat.external_id
                    )
                )
                if exists.scalar():
                    continue

                distance = calc_distance(
                    user_filters["lat"],
                    user_filters["lon"],
                    flat.lat,
                    flat.lon,
                )

                # scrape_description is synchronous/blocking - run in thread
                description = await asyncio.to_thread(scrape_description, flat.url)

                session.add(
                    Apartment(
                        external_id=flat.external_id,
                        price=flat.price,
                        floor=flat.floor,
                        lat=flat.lat,
                        lon=flat.lon,
                        distance=distance,
                        description=description,
                        url=flat.url,
                        approved=False,
                    )
                )

            await session.commit()

        await asyncio.sleep(FOUR_HOURS)
