import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from db import init_db, Session
from models import Apartment
from filters import user_filters
from cron_task import cron_parser, filters_ready
from sqlalchemy import select

router = Router()

# configure logging early so imports that run work (cron_task may run on import)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

def approve_kb(apt_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{apt_id}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{apt_id}")
    ]])

@router.message(Command("start"))
async def start(msg: Message):
    await msg.answer(
        "/set_point lat lon\n"
        "/set_price min max\n"
        "/set_floor min max\n"
        "/show"
    )

@router.message(Command("set_point"))
async def set_point(msg: Message):
    _, lat, lon = msg.text.split()
    user_filters["lat"] = float(lat)
    user_filters["lon"] = float(lon)
    logger.info("User %s set point to %s,%s", getattr(msg.from_user, 'id', 'unknown'), lat, lon)
    logger.info("Current filters: %s", user_filters)
    # wake the cron loop so scraping can start immediately
    try:
        filters_ready.set()
    except Exception:
        logger.exception("Failed to set filters_ready event")
    await msg.answer("📍 Точка обновлена")

@router.message(Command("set_price"))
async def set_price(msg: Message):
    _, mn, mx = msg.text.split()
    user_filters["price_min"] = int(mn)
    user_filters["price_max"] = int(mx)
    logger.info("User %s set price range %s-%s", getattr(msg.from_user, 'id', 'unknown'), mn, mx)
    logger.info("Current filters: %s", user_filters)
    try:
        filters_ready.set()
    except Exception:
        logger.exception("Failed to set filters_ready event")
    await msg.answer("💰 Цена обновлена")

@router.message(Command("set_floor"))
async def set_floor(msg: Message):
    _, mn, mx = msg.text.split()
    user_filters["floor_min"] = int(mn)
    user_filters["floor_max"] = int(mx)
    logger.info("User %s set floor range %s-%s", getattr(msg.from_user, 'id', 'unknown'), mn, mx)
    logger.info("Current filters: %s", user_filters)
    try:
        filters_ready.set()
    except Exception:
        logger.exception("Failed to set filters_ready event")
    await msg.answer("🏢 Этаж обновлён")


@router.message(Command("clear_filters"))
async def clear_filters(msg: Message):
    user_filters.clear()
    logger.info("User %s cleared filters", getattr(msg.from_user, 'id', 'unknown'))
    # Do not set filters_ready; cron loop will wait until filters are set again
    await msg.answer("Filters cleared. Please set /set_point, /set_price and /set_floor to start scraping.")

@router.message(Command("show"))
async def show(msg: Message):
    logger.info("User %s requested show with filters=%s", getattr(msg.from_user, 'id', 'unknown'), user_filters)
    async with Session() as session:
        q = select(Apartment).where(
            Apartment.price >= user_filters["price_min"],
            Apartment.price <= user_filters["price_max"],
            Apartment.floor >= user_filters["floor_min"],
            Apartment.floor <= user_filters["floor_max"]
        ).order_by(Apartment.distance.asc())

        res = await session.execute(q)
        apts = res.scalars().all()
        logger.info("Query returned %d apartments", len(apts))

        if not apts:
            await msg.answer("No apartments found for your filters.")
            return

        # limit flood of messages — send at most 20 at once
        max_send = 20
        if len(apts) > max_send:
            await msg.answer(f"Found {len(apts)} apartments, showing first {max_send}...")

        for apt in apts[:max_send]:
            try:
                distance_text = f"{int(apt.distance)} м" if apt.distance is not None else "N/A"
                text = (
                    f"🏠 {apt.price} €\n"
                    f"🏢 этаж {apt.floor}\n"
                    f"📍 {distance_text}\n\n"
                    f"{apt.description[:800]}\n\n"
                    f"{apt.url}"
                )
                await msg.answer(text, reply_markup=approve_kb(apt.id))
            except Exception:
                logger.exception("Failed to send apartment %s to user %s", apt.id, getattr(msg.from_user, 'id', 'unknown'))

@router.callback_query(F.data.startswith("approve:"))
async def approve(cb):
    apt_id = int(cb.data.split(":")[1])
    async with Session() as session:
        apt = await session.get(Apartment, apt_id)
        apt.approved = True
        await session.commit()
    await cb.answer("Approved")

@router.callback_query(F.data.startswith("reject:"))
async def reject(cb):
    apt_id = int(cb.data.split(":")[1])
    async with Session() as session:
        apt = await session.get(Apartment, apt_id)
        await session.delete(apt)
        await session.commit()
    await cb.answer("Deleted")
    await cb.message.delete()

async def main():
    logger.info("Initializing database")
    await init_db()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("Starting cron parser task")
    asyncio.create_task(cron_parser())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
