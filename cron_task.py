import asyncio
import logging
from scraper.map_scraper import SsMapScraper
from db import Session
from models import Apartment
from utils import calc_distance
from filters import user_filters
from sqlalchemy import select

FOUR_HOURS = 4 * 60 * 60

logger = logging.getLogger(__name__)

scraper = SsMapScraper()
filters_ready = asyncio.Event()


async def cron_parser():
    """Main cron loop: runs the blocking map scraper in a thread and stores new flats."""
    while True:
        try:
            # Wait until required user filters are set before scraping.
            required = [
                "lat",
                "lon",
                "price_min",
                "price_max",
                "floor_min",
                "floor_max",
            ]
            # keep checking until all required filters are present; we wait on
            missing = [k for k in required if k not in user_filters]
            while missing:
                logger.info("Waiting for user filters to be set, missing: %s", missing)
                try:
                    await asyncio.wait_for(filters_ready.wait(), timeout=30)

                    filters_ready.clear()
                except asyncio.TimeoutError:
                    pass
                missing = [k for k in required if k not in user_filters]

            logger.info("Starting map scrape")
            flats = await asyncio.to_thread(scraper.scrape)
            logger.info("Map scrape complete, found %d markers", len(flats))

            # Ignore markers that don't have an external_id/url
            valid_flats = [f for f in flats if f.external_id]
            skipped = len(flats) - len(valid_flats)
            if skipped:
                logger.warning("Skipping %d markers with empty external_id/url", skipped)

            added = 0
            async with Session() as session:
                for flat in flats:
                    if not flat.external_id:
                        continue
                    exists = await session.execute(
                        select(Apartment).where(
                            Apartment.external_id == flat.external_id
                        )
                    )
                    if exists.scalar():
                        logger.debug("Skipping existing apt %s", flat.external_id)
                        continue

                    distance = calc_distance(
                        user_filters["lat"],
                        user_filters["lon"],
                        flat.lat,
                        flat.lon,
                    )


                    session.add(
                        Apartment(
                            external_id=flat.external_id,
                            price=flat.price,
                            floor=flat.floor,
                            lat=flat.lat,
                            lon=flat.lon,
                            distance=distance,
                            url=flat.url,
                            approved=False,
                        )
                    )
                    added += 1

                if added:
                    await session.commit()
                    logger.info("Committed %d new apartments", added)
                else:
                    logger.info("No new apartments to commit")

        except Exception:
            logger.exception("Error occurred in cron_parser loop")

        logger.info("Sleeping for %d seconds", FOUR_HOURS)
        await asyncio.sleep(FOUR_HOURS)
