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
from datetime import datetime, timedelta
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer
from Sources.files import languages
import os


async def awarding(user_id, start_award: float, line_difference: int, conn, bot: Bot):
    award = start_award/(2**line_difference)
    #print(award)
    user_info = await conn.fetchrow("SELECT blocking, referer_id, tg_user_id, language_code, show_award_notifications FROM accounts WHERE id = $1", user_id)
    if user_info["blocking"] == None:
        await conn.execute("UPDATE accounts SET bonuses = bonuses + $1 WHERE id = $2", award, user_id)

        await conn.execute("INSERT INTO logs (description, date) VALUES ($1, $2)", f"Award. acc_id = {str(user_id)}, award = {str(award)}", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))))
        print(f"Award. acc_id = {str(user_id)}, award = {str(award)}")

        if user_info["show_award_notifications"] == True and user_info["tg_user_id"] != None:
            try:
                await bot.send_message(chat_id=user_info["tg_user_id"], text=languages[user_info["language_code"]]["texts"]["notifications"]["new_award"] + str(award))
            except Exception as e:
                print(e)
                print(e.__traceback__)
    line_difference += 1
    referer_id = user_info["referer_id"]
    if referer_id != None:
        await awarding(referer_id, start_award, line_difference, conn, bot)
    

