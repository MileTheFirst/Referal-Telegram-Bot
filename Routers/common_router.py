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
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer
from Sources.files import languages

from Sources.files import set_last_tariff_check_date

import os

from datetime import datetime

common_router = Router()

common_router.message.filter(MagicData(F.is_auth.is_(True)))
common_router.callback_query.filter(MagicData(F.is_auth.is_(True)))


#-----------------------------------------------------------------------------------------------------------------


@common_router.callback_query(F.data == "account")
async def acc_menu(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    try: 
        user_info = await conn.fetchrow("SELECT bonuses, id, tg_user_id, role, blocking, show_award_notifications FROM accounts WHERE tg_user_id = $1", query.from_user.id)

        #text = languages[lang_code]["texts"]["acc_text"]["telegram_id"] + str(user_info["tg_user_id"]) + "\n"
        text = languages[lang_code]["texts"]["acc_text"]["id"] + str(user_info["id"]) + "\n"
        if user_info["bonuses"] != None:
            text += languages[lang_code]["texts"]["acc_text"]["bonuses"] + str(user_info['bonuses']) + "\n"
        text += languages[lang_code]["texts"]["acc_text"]["acc_settings"]

        builder = InlineKeyboardBuilder()
        builder.button(text=languages[lang_code]["keyboards"]["base_acc_menu"]["language"], callback_data="language")
        if user_info['role'] == "user":
            if user_info["blocking"] == None:
                if await conn.fetchval("SELECT COUNT(*) FROM accounts WHERE referer_id = $1", user_info["id"]) == 0 and await conn.fetchval("SELECT COUNT(*) FROM catalogs WHERE owner_id = $1", user_info["id"]) == 0:        
                    builder.button(text=languages[lang_code]["keyboards"]["base_acc_menu"]["wait_attach"], callback_data="wait_attach")
            elif user_info["blocking"] == "waiting_attach":
                builder.button(text=languages[lang_code]["keyboards"]["base_acc_menu"]["stop_wait_attach"], callback_data="stop_wait_attach")

        if user_info["show_award_notifications"] == True:
            builder.button(text=languages[lang_code]["keyboards"]["base_acc_menu"]["disable_award_notifications"], callback_data="disable_award_notifications")
        elif user_info["show_award_notifications"] == False:
            builder.button(text=languages[lang_code]["keyboards"]["base_acc_menu"]["enable_award_notifications"], callback_data="enable_award_notifications")

        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
        builder.adjust(1)
        
        await query.message.edit_text(text)
        await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    except Exception as e:
        print(e)
        print(e.__traceback__)
        await query.message.edit_text(languages[lang_code]["answers"]["errors"]["smth"])
        await query.message.edit_reply_markup(reply_markup=back_kb("main_menu", lang_code))
    finally:
        await conn.close()

@common_router.callback_query(F.data == "enable_award_notifications")
async def enable_award_notifications(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    await conn.execute("UPDATE accounts SET show_award_notifications = true WHERE tg_user_id = $1", query.from_user.id)

    await conn.close()
    await acc_menu(query, lang_code)

@common_router.callback_query(F.data == "disable_award_notifications")
async def enable_award_notifications(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    await conn.execute("UPDATE accounts SET show_award_notifications = false WHERE tg_user_id = $1", query.from_user.id)

    await conn.close()
    await acc_menu(query, lang_code)

@common_router.callback_query(F.data == "language")
async def language(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    try:
        text = languages[lang_code]["texts"]["language_text"]["language"] + lang_code + "\n"
        text += languages[lang_code]["texts"]["language_text"]["l_m"]

        builder = InlineKeyboardBuilder()
        for key in languages:
            builder.button(text=key, callback_data="choose_language!" + key)
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="account")
        builder.adjust(1)

        await query.message.edit_text(text)
        await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    except Exception as e:
        print(e)
        print(e.__traceback__)
        await query.message.edit_text(languages[lang_code]["answers"]["errors"]["smth"])
        await query.message.edit_reply_markup(reply_markup=back_kb("account", lang_code))
    finally:
        await conn.close()

@common_router.callback_query(CallbackArgFilter("choose_language"))
async def choose_language(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    try:
        lang_code = query.data.split("!")[1]
        await conn.execute("UPDATE accounts SET language_code = $1 WHERE tg_user_id = $2", lang_code, query.from_user.id)
        await query.message.edit_text(languages[lang_code]["answers"]["common_router"]["choose_language"])   
    except Exception as e:
        print(e)
        print(e.__traceback__)
        await query.message.edit_text(languages[lang_code]["answers"]["errors"]["smth"])
    finally:
        await query.message.edit_reply_markup(reply_markup=back_kb("language", lang_code))
        await conn.close()


#----------------------------------------------------------------------------------------------------------------------


@common_router.callback_query(F.data == "my_catalogs")
async def my_catalogs(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    owner_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    catalogs = await conn.fetch("SELECT id, name FROM catalogs WHERE owner_id = $1", owner_id)
    await query.message.edit_text(languages[lang_code]["answers"]["common_router"]["my_catalogs"])
    await query.message.edit_reply_markup(reply_markup=my_catalogs_menu_kb(catalogs, lang_code))
    await conn.close()

#-----------------------------------------------------------------------------------------------------
    
@common_router.callback_query(F.data == "tariffs")
async def tariffs(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    user_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", user_id)
    tariffs = await conn.fetch("SELECT tariff FROM tariff_params ORDER BY price_p_m")

    #text = languages[lang_code]["texts"]["acc_text"]["tariff_1"] + tariff + "\n"
    text = languages[lang_code]["texts"]["acc_text"]["tariff_1"] + languages[lang_code]["texts"]["tariffs"][tariff] + "\n"
    text += languages[lang_code]["texts"]["acc_text"]["tariff_2"]
    await query.message.edit_text(text=text)
    await query.message.edit_reply_markup(reply_markup=tariffs_kb(tariffs, lang_code))

    await conn.close()


