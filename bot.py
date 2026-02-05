import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from db import init_db, Session
from models import Apartment
from filters import user_filters
from cron_task import cron_parser
from sqlalchemy import select

router = Router()

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
    await msg.answer("📍 Точка обновлена")

@router.message(Command("set_price"))
async def set_price(msg: Message):
    _, mn, mx = msg.text.split()
    user_filters["price_min"] = int(mn)
    user_filters["price_max"] = int(mx)
    await msg.answer("💰 Цена обновлена")

@router.message(Command("set_floor"))
async def set_floor(msg: Message):
    _, mn, mx = msg.text.split()
    user_filters["floor_min"] = int(mn)
    user_filters["floor_max"] = int(mx)
    await msg.answer("🏢 Этаж обновлён")

@router.message(Command("show"))
async def show(msg: Message):
    async with Session() as session:
        q = select(Apartment).where(
            Apartment.price >= user_filters["price_min"],
            Apartment.price <= user_filters["price_max"],
            Apartment.floor >= user_filters["floor_min"],
            Apartment.floor <= user_filters["floor_max"]
        ).order_by(Apartment.distance.asc())

        res = await session.execute(q)

        for apt in res.scalars():
            await msg.answer(
                f"🏠 {apt.price} €\n"
                f"🏢 этаж {apt.floor}\n"
                f"📍 {int(apt.distance)} м\n\n"
                f"{apt.description[:800]}\n\n"
                f"{apt.url}",
                reply_markup=approve_kb(apt.id)
            )

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
    await init_db()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    asyncio.create_task(cron_parser())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
