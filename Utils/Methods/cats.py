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

async def complect_subcats(line: list, conn, cat_list: list) -> list:
    next_line = []
    for cat in line:
        cat_list.append(cat["id"])
        subcats = await conn.fetch("SELECT id FROM categories WHERE parent_cat_id = $1", cat["id"])
        for subcat in subcats:
            next_line.append(subcat)
    if next_line != []:
        await complect_subcats(next_line, conn, cat_list)
    
    




    # if next_line != []:
    #     return cat_list + await complect_subcats(next_line, conn, cat_list)
    # else:
    #     return cat_list

    
    
    