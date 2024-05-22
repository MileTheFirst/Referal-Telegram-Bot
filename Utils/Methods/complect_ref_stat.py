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

async def complect_ref_stat(user_id, conn) -> dict:
    next_line = await conn.fetch("SELECT id FROM accounts WHERE referer_id = $1", user_id)
    return await complecting(next_line, conn, [], 0)

async def complecting(line, conn, lines_list: list, full_count) -> dict:
    next_line = []
    count = 0
    for row in line:
        count += 1
        next_line = next_line + await conn.fetch("SELECT id FROM accounts WHERE referer_id = $1", row["id"])
    lines_list.append(count)
    full_count += count
    if len(next_line) > 0:
        complected = await complecting(next_line, conn, lines_list, full_count)
        return {"lines_list": complected["lines_list"], "full_count": complected["full_count"]}
    else:
        return {"lines_list": lines_list, "full_count": full_count}
