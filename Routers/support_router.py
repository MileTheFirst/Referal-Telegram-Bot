from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.tariff_kbs import tariffs_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu, support_main_menu_kb
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
from Sources.files import s3
from Sources.files import remove_product_media_dir, old_remove_product_media_dir, remove_catalog_media, old_get_catalogs_dir_path, old_remove_catalog_media, old_add_catalog_media_file, old_add_product_media_file, old_get_catalog_album_builder, old_get_product_album_builder, old_get_products_dir_path, old_make_product_media_dir, add_catalog_media_file, add_product_media_file, get_catalog_album_builder, get_product_album_builder

from Sources.files import set_last_tariff_check_date

import os

from datetime import datetime, timedelta

import pytz



support_router = Router()

support_router.message.filter(RoleFilter("support"))
support_router.callback_query.filter(RoleFilter("support"))


@support_router.callback_query(F.data == "main_menu")
async def main_menu(query:CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    cbck_message = await query.message.answer(languages[lang_code]["answers"]["menus"]["menu"], reply_markup=support_main_menu_kb(lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)
    await conn.close()

@support_router.message(Command("menu"))
async def main_menu_cbck(message: Message, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    
    cbck_message = await message.answer(text=languages[lang_code]["answers"]["menus"]["menu"], reply_markup=support_main_menu_kb(lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await conn.close()


@support_router.callback_query(F.data == "moderate_catalogs")
async def moderate_catalogs(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    acc_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", query.from_user.id)

    moderate_list = await conn.fetch("SELECT * FROM moderation_list WHERE moderator_id = $1 and moderation_date IS NULL", acc_id)

    builder = InlineKeyboardBuilder()
    for moderation in moderate_list:
        catalog = await conn.fetchrow("SELECT * FROM catalogs WHERE id = $1", moderation["catalog_id"])
        builder.button(text=catalog["name"], callback_data="moderate_catalog!" + str(catalog["id"]))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)

    await query.message.edit_text(text=languages[lang_code]["answers"]["support_router"]["moderate_catalogs"])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()

@support_router.callback_query(CallbackArgFilter("moderate_catalog"))
async def moderate_catalog(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    catalog_id = int(query.data.split("!")[1])
    products = await conn.fetch("SELECT id, name FROM products WHERE catalog_id = $1", catalog_id)
    catalog_info = await conn.fetchrow("SELECT name, owner_id, status FROM catalogs WHERE id = $1", catalog_id)
    owner_info = await conn.fetchrow("SELECT login FROM accounts WHERE id = $1", catalog_info["owner_id"])

    ####
    album_builder = get_catalog_album_builder(catalog_id)
    ####
    ####
    # album_builder = old_get_catalog_album_builder(catalog_id)
    ####

    messages_to_wait = []
        
    media=album_builder.build()
    group = []
    if media != []:
        group = await query.message.answer_media_group(media=media)

    for mess in group:
        messages_to_wait.append(mess)

    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(text=product["name"], callback_data= "view_moderating_product!" + str(product["id"]))
    builder.button(text=languages[lang_code]["keyboards"]["support_router"]["moderate_catalog_menu"]["approve"], callback_data="approve_catalog!"+str(catalog_id))
    builder.button(text=languages[lang_code]["keyboards"]["support_router"]["moderate_catalog_menu"]["reject"], callback_data="reject_catalog!"+str(catalog_id))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="moderate_catalogs")
    builder.adjust(1)

    text = languages[lang_code]["texts"]["catalog_text"]["owner"] + owner_info["login"] + "\n"
    text += languages[lang_code]["texts"]["catalog_text"]["status"] + catalog_info["status"] + "\n"
    text += languages[lang_code]["texts"]["catalog_text"]["catalog"] + catalog_info['name'] +":"

    messages_to_wait.append(await query.message.answer(text=text, reply_markup=builder.as_markup()))

    for mess in messages_to_wait:
        await add_to_waiting_cbck_buffer(conn, mess)
    await delete_cbck_message(conn, query.message)
    
    await conn.close()

@support_router.callback_query(CallbackArgFilter("approve_catalog"))
async def approve_catalog(query: CallbackQuery, bot: Bot, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])
    
    catalog_info = await conn.fetchrow("SELECT owner_id, name FROM catalogs WHERE id = $1", catalog_id)
    user_info = await conn.fetchrow("SELECT tg_user_id, language_code, blocking FROM accounts WHERE id = $1", catalog_info["owner_id"])

    await conn.execute("UPDATE catalogs SET status = 'approved' WHERE id = $1", catalog_id)

    await conn.execute("UPDATE moderation_list SET status = 'approved', moderation_date = $1 WHERE catalog_id = $2", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))), catalog_id)

    not_text = languages[user_info["language_code"]]["texts"]["notifications"]["catalog_approved"] + catalog_info["name"]
    try:
        await bot.send_message(chat_id=user_info["tg_user_id"], text=not_text)
    except Exception as e:
        print(e)
        print(e.__traceback__)

    await query.message.edit_text(text=languages[lang_code]["answers"]["support_router"]["catalog_approved"])
    await query.message.edit_reply_markup(reply_markup=back_kb("moderate_catalogs", lang_code))

    await conn.close()


@support_router.callback_query(CallbackArgFilter("reject_catalog"))
async def reject_catalog(query: CallbackQuery, bot: Bot, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])
    
    text=languages[lang_code]["answers"]["support_router"]["catalog_rejected"]

    catalog_info = await conn.fetchrow("SELECT owner_id, name FROM catalogs WHERE id = $1", catalog_id)
    user_info = await conn.fetchrow("SELECT tg_user_id, language_code, blocking FROM accounts WHERE id = $1", catalog_info["owner_id"])

    await conn.execute("UPDATE catalogs SET status = 'rejected' WHERE id = $1", catalog_id)

    await conn.execute("UPDATE moderation_list SET status = 'rejected', moderation_date = $1 WHERE catalog_id = $2", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))), catalog_id)

    not_text = languages[lang_code]["texts"]["notifications"]["catalog_rejected"] + catalog_info["name"]
    try:
        await bot.send_message(chat_id=user_info["tg_user_id"], text=not_text)
    except Exception as e:
        print(e)
        print(e.__traceback__)

    #await conn.execute("INSERT INTO violation_list (user_id, catalog_id) VALUES ($1, $2)", catalog_info["owner_id"], catalog_id)
    #violation_count = await conn.fetchval("SELECT COUNT(*) FROM violation_list WHERE user_id = $1", catalog_info["owner_id"])
    violation_count = await conn.fetchval("SELECT COUNT(*) FROM moderation_list WHERE user_id = $1 and status = 'rejected'", catalog_info["owner_id"])
    
    if violation_count > 1:
        await conn.execute("UPDATE accounts SET role = $1, blocking = $2 WHERE id = $3", "user", "blocked", catalog_info["owner_id"])
    
        not_text = languages[user_info["language_code"]]["texts"]["notifications"]["blocking"]
        try:
            await bot.send_message(chat_id=user_info["tg_user_id"], text=not_text)
        except Exception as e:
            print(e)
            print(e.__traceback__)

        await conn.execute("UPDATE moderation_list SET status = 'user_blocked', moderation_date = $1 WHERE catalog_id = $2", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))), catalog_id)

        text += "\n" + languages[lang_code]["answers"]["support_router"]["user_blocked"]

    await query.message.edit_text(text)
    await query.message.edit_reply_markup(reply_markup=back_kb("moderate_catalogs", lang_code))

    await conn.close()


@support_router.callback_query(F.data == "moderate_withdrawals")
async def moderate_catalogs(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    acc_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", query.from_user.id)

    moderate_list = await conn.fetch("SELECT * FROM withdrawal_list WHERE moderator_id = $1 AND moderation_date IS NULL", acc_id)
    #print(moderate_list)

    builder = InlineKeyboardBuilder()
    for withdrawal in moderate_list:
        builder.button(text=str(withdrawal["user_id"]), callback_data="moderate_withdrawal!" + str(withdrawal["id"]))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)

    await query.message.edit_text(text=languages[lang_code]["answers"]["support_router"]["moderate_withdrawals"])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()


@support_router.callback_query(CallbackArgFilter("moderate_withdrawal"))
async def moderate_withdrawals(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    withdrawal_id = int(query.data.split("!")[1])
    withdrawal_info = await conn.fetchrow("SELECT * FROM withdrawal_list WHERE id = $1", withdrawal_id)
    user_info = await conn.fetchrow("SELECT id, bonuses, login, tg_user_id FROM accounts WHERE id = $1", withdrawal_info["user_id"])

    text = languages[lang_code]["texts"]["acc_text"]["login"] + user_info["login"] + "\n"
    #text += languages[lang_code]["texts"]["acc_text"]["telegram_id"] + str(user_info["tg_user_id"]) + "\n"
    text += languages[lang_code]["texts"]["acc_text"]["id"] + str(user_info["id"]) + "\n"
    text += languages[lang_code]["texts"]["acc_text"]["bonuses"] + str(user_info["bonuses"]) + "\n"
    text += languages[lang_code]["texts"]["withdrawal_text"]["id"] + str(withdrawal_id) + "\n"
    text += languages[lang_code]["texts"]["withdrawal_text"]["amount"] + str(withdrawal_info["amount"]) + "\n"
    text += languages[lang_code]["texts"]["withdrawal_text"]["bank_card_number"] + withdrawal_info["bank_card_number"] + "\n"

    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["finish"], callback_data="finish_withdrawal!" + str(withdrawal_id))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["reject"], callback_data="reject_withdrawal!" + str(withdrawal_id))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="moderate_withdrawals")
    builder.adjust(1)

    await query.message.edit_text(text=text + languages[lang_code]["answers"]["menus"]["menu"])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()


@support_router.callback_query(CallbackArgFilter("finish_withdrawal"))
async def finish_withdrawal(query: CallbackQuery, bot: Bot, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    withdrawal_id = int(query.data.split("!")[1])

    withdrawal_info = await conn.fetchrow("SELECT * FROM withdrawal_list WHERE id = $1", withdrawal_id)
    #user_info = await conn.fetchrow("SELECT id, tg_user_id FROM accounts WHERE id = $1", withdrawal_info["user_id"])

    await conn.execute("UPDATE accounts SET bonuses = bonuses - $1 WHERE id = $2", withdrawal_info["amount"], withdrawal_info["user_id"])
    await conn.execute("UPDATE withdrawal_list SET bank_card_number = NULL, status = 'finished', moderation_date = $1 WHERE id = $2", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))), withdrawal_id)

    user_info = await conn.fetchrow("SELECT id, tg_user_id, language_code FROM accounts WHERE id = $1", withdrawal_info["user_id"])
    not_text = languages[user_info["language_code"]]["texts"]["notifications"]["withdrawal_finished"] + str(withdrawal_id)
    try:
        await bot.send_message(chat_id=user_info["tg_user_id"], text=not_text)
    except Exception as e:
        print(e)
        print(e.__traceback__)

    await query.message.edit_text(text=languages[lang_code]["answers"]["support_router"]["finish_withdrawal"])
    await query.message.edit_reply_markup(reply_markup=back_kb("moderate_withdrawals", lang_code))

    await conn.close()


@support_router.callback_query(CallbackArgFilter("reject_withdrawal"))
async def finish_withdrawal(query: CallbackQuery, bot: Bot,  lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    withdrawal_id = int(query.data.split("!")[1])

    withdrawal_info = await conn.fetchrow("SELECT * FROM withdrawal_list WHERE id = $1", withdrawal_id)
    user_info = await conn.fetchrow("SELECT id, tg_user_id, language_code FROM accounts WHERE id = $1", withdrawal_info["user_id"])

    await conn.execute("UPDATE withdrawal_list SET bank_card_number = NULL, status = 'rejected', moderation_date = $1 WHERE id = $2", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))), withdrawal_id)

    not_text = languages[user_info["language_code"]]["texts"]["notifications"]["your_withdrawal_rejected"] + str(withdrawal_id)

    try:
        await bot.send_message(chat_id=user_info["tg_user_id"], text=not_text)
    except Exception as e:
        print(e)
        print(e.__traceback__)

    await query.message.edit_text(text=languages[lang_code]["answers"]["support_router"]["reject_withdrawal"])
    await query.message.edit_reply_markup(reply_markup=back_kb("moderate_withdrawals", lang_code))

    await conn.close()