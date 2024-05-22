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

async def insert_into_products(catalog_id: int, cat_id: int, name: str, desc: str, conn) -> int:
    product_id = await conn.fetchval('''INSERT INTO products 
                (catalog_id, category_id, name, description, tsvector_desc) 
            VALUES 
                ($1, $2, $3, $4, to_tsvector($4)) 
            RETURNING id''', catalog_id, cat_id, name, desc)
    return product_id

async def update_product_desc(product_id: int, desc: str, conn):
    await conn.execute('''UPDATE products 
            SET 
                description = $1, tsvector_desc = to_tsvector($1) 
            WHERE id = $2''', desc, product_id)
