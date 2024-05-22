from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.tariff_kbs import tariffs_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from Utils.Keyboards.catalogs_products_kbs import my_catalogs_menu_kb, my_product_menu_kb
from States.auth_states import InvitedRegForm
from Filters.filters import CallbackArgFilter
from aiogram.utils.media_group import MediaGroupBuilder
from Utils.Methods.complect_ref_stat import complect_ref_stat

from Utils.Methods.mailing import permanent_mailing_task
from Utils.Methods.tariff_upd import permanent_tariff_update_task
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Filters.filters import RoleFilter
from Sources.files import languages
import random

from Sources.files import set_last_tariff_check_date

import os

from datetime import datetime


user_router = Router()

user_router.message.filter(RoleFilter("user"))
user_router.callback_query.filter(RoleFilter("user"))


@user_router.message(Command("menu"))
@user_router.callback_query(F.data == "main_menu")
async def main_menu(update: CallbackQuery | Message, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    #acc_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", update.from_user.id)
    #tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = True", acc_id)
    # show_find_products_but = True
    # if tariff == "base":
    #     show_find_products_but = False

    if isinstance(update, CallbackQuery):
        cbck_message = await update.message.answer(languages[lang_code]["answers"]["menus"]["menu"], reply_markup=user_main_menu_kb(lang_code))
        await delete_cbck_message(conn, update.message)
    elif isinstance(update, Message):
        cbck_message = await update.answer(languages[lang_code]["answers"]["menus"]["menu"], reply_markup=user_main_menu_kb(lang_code))
    
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await conn.close()

# @user_router.message(Command("menu"))
# async def main_menu_cbck(message: Message, lang_code: str = None):
#     conn = await asyncpg.connect(**connection_params)

#     #print(message.from_user.username)

#     acc_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", message.from_user.id)
#     tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = True", acc_id)
#     show_find_products_but = True
#     if tariff == "base":
#         show_find_products_but = False
    
#     cbck_message = await message.answer(languages[lang_code]["answers"]["menus"]["menu"], reply_markup=user_main_menu_kb(lang_code, show_find_products_but))
#     await add_to_waiting_cbck_buffer(conn, cbck_message)
#     await conn.close()


@user_router.callback_query(F.data == "view_ref_stat")
async def view_ref_link(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    user_info = await conn.fetchrow("SELECT ref_link, id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    if user_info["ref_link"] != None:
        ref_stat = await complect_ref_stat(user_info["id"], conn)
        line_number = 1
        line_text = ""
        for line_count in ref_stat["lines_list"]:
            line_text += languages[lang_code]["texts"]["ref_stat_text"]["line"] + str(line_number) + ": "  + str(line_count) + "\n"
            line_number += 1

        text = languages[lang_code]["texts"]["ref_stat_text"]["ref_description"] + "\n\n"
        text += languages[lang_code]["texts"]["ref_link"] + f"{ os.getenv('BOT_LINK') }?start=ref{ user_info['ref_link'] } \n\n"
        text += line_text
        text += languages[lang_code]["texts"]["ref_stat_text"]["amount"] + str(ref_stat["full_count"])
        await query.message.edit_text(text=text)
        await query.message.edit_reply_markup(reply_markup=back_kb("main_menu", lang_code))
    else:
        await query.message.edit_reply_markup(reply_markup=gen_ref_link_kb(lang_code))
    await conn.close()

@user_router.callback_query(F.data == "gen_ref_link")
async def gen_ref_link(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    #login = await conn.fetchval("SELECT login FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    code = str(query.from_user.id) + str(random.randint(-1000000, 1000000))
    ref_link = hashlib.sha256(code.encode()).hexdigest()
    ref_link = ref_link[0:50]

    await conn.execute("UPDATE accounts SET ref_link = $1 WHERE tg_user_id = $2", ref_link, query.from_user.id)

    await query.message.edit_text(languages[lang_code]["answers"]["user_router"]["ref_link_gened"])
    await query.message.edit_reply_markup(reply_markup=gened_ref_link_kb(lang_code))
    await conn.close()

@user_router.callback_query(F.data == "wait_attach")
async def wait_for_attach(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    user_info = await conn.fetchrow("SELECT blocking, id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    if user_info["blocking"] == None:
        if await conn.fetchval("SELECT COUNT(*) FROM accounts WHERE referer_id = $1", user_info["id"]) == 0 and await conn.fetchval("SELECT COUNT(*) FROM catalogs WHERE owner_id = $1", user_info["id"]) == 0:
            await conn.execute("UPDATE accounts SET blocking = 'waiting_attach' WHERE tg_user_id = $1", query.from_user.id)

    await query.message.edit_text(languages[lang_code]["answers"]["user_router"]["started_waiting_attach"])
    await query.message.edit_reply_markup(reply_markup=back_kb("account", lang_code))

    await conn.close()

@user_router.callback_query(F.data == "stop_wait_attach")
async def wait_for_attach(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    await conn.execute("UPDATE accounts SET blocking = NULL WHERE tg_user_id = $1", query.from_user.id)

    await query.message.edit_text(languages[lang_code]["answers"]["user_router"]["stoped_waiting_attach"])
    await query.message.edit_reply_markup(reply_markup=back_kb("account", lang_code))

    await conn.close()
