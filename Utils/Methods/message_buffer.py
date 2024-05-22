from aiogram import Router, types, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.special_kbs import sign_in_or_up_kb
from Filters.filters import StatesFilter

async def passed_add_to_waiting_cbck_buffer(conn, message: Message):
    pass

async def add_to_waiting_cbck_buffer(conn, message: Message):
    await conn.execute("INSERT INTO waiting_cbck_buffer (chat_id, message_id) VALUES ($1, $2)", message.chat.id, message.message_id)

async def passed_del_from_waiting_cbck_buffer(conn, message: Message):
    pass

async def del_from_waiting_cbck_buffer(conn, message: Message):
    await conn.execute("DELETE FROM waiting_cbck_buffer WHERE chat_id = $1 and message_id = $2", message.chat.id, message.message_id)

async def delete_cbck_message(conn, message: Message):
    try:
        await message.delete()
    except Exception as e:
            print(e)
            print(e.__traceback__)
    finally:
         await del_from_waiting_cbck_buffer(conn, message)