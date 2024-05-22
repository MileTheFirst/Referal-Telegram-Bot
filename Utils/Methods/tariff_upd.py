from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.special_kbs import sign_in_or_up_kb
from Utils.Keyboards.catalogs_products_kbs import received_catalog_kb
from Filters.filters import StatesFilter
from datetime import datetime, timedelta, timezone
from Sources.files import get_last_tariff_check_date, set_last_tariff_check_date

import pytz
import os


async def permanent_tariff_update_task():
    conn = await asyncpg.connect(**connection_params)

    last_check_date = get_last_tariff_check_date()
    
    active_tariffs = await conn.fetch("SELECT * FROM tariff_buffer WHERE is_active = true")

    for tariff in active_tariffs:
        time_difference = datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))) - last_check_date
        remains = None
        if tariff["remains"] != None:
            remains = tariff["remains"] - time_difference
        await conn.execute("UPDATE tariff_buffer SET remains = $1 WHERE id = $2", remains, tariff["id"])

    overdue_tariffs = await conn.fetch("SELECT * FROM tariff_buffer WHERE remains < $1", timedelta(seconds=10))
    for tariff in overdue_tariffs:
        await conn.execute("DELETE FROM tariff_buffer WHERE id = $1", tariff["id"])
        await conn.execute("UPDATE tariff_buffer SET is_active = true WHERE user_id = $1 and tariff = 'base'", tariff["user_id"])

    set_last_tariff_check_date(datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))))

    await conn.close()




async def add_to_tariff_buffer(user_id: int, term: timedelta, conn, tariff: str = "base") -> bool:
    if await conn.fetchval("SELECT COUNT(*) FROM tariff_buffer WHERE user_id = $1 and tariff = $2", user_id, tariff) > 0:
        return False
    else:
        await conn.execute('''
            INSERT INTO tariff_buffer (tariff, user_id, is_active, remains) VALUES ($1, $2, $3, $4)
        ''', tariff, user_id, False, term)
        
        return True
    

async def activate_in_tariff_buffer(user_id: int, conn, tariff: str = "base"):
    await conn.execute("UPDATE tariff_buffer SET is_active = false WHERE user_id = $1 and is_active = true", user_id)
    await conn.execute("UPDATE tariff_buffer SET is_active = true WHERE user_id = $1 and tariff = $2 ", user_id, tariff)



