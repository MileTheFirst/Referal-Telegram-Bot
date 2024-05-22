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

async def find_free_moderator(pre_moderators: list, conn):
    moderator = None
    last_min_count = None
    for pre_moderator in pre_moderators:
        under_moderator_count = await conn.fetchval("SELECT COUNT(*) FROM moderation_list WHERE moderator_id = $1", pre_moderator["id"])
        if last_min_count == None or under_moderator_count < last_min_count:
            moderator = pre_moderator
            last_min_count = under_moderator_count
    return moderator

async def reset_moderator(acc_id: int, conn):
    pre_moderators = await conn.fetch("SELECT * FROM accounts WHERE role = 'support' and tg_user_id IS NOT NULL and id != $1", acc_id)
    moderator = await find_free_moderator(pre_moderators, conn)

    await conn.execute("UPDATE moderation_list SET moderator_id = $1 WHERE moderator_id = $2", moderator["id"], acc_id)

    