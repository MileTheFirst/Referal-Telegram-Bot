from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.special_kbs import sign_in_or_up_kb
from Utils.Keyboards.catalogs_products_kbs import received_catalog_kb, received_products_in_catalog_menu_kb
from Filters.filters import StatesFilter
from datetime import datetime, timedelta, timezone
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer
from Sources.files import languages
from aiogram.utils.media_group import MediaGroupBuilder
from Sources.files import s3
from Sources.files import remove_product_media_dir, old_remove_product_media_dir, remove_catalog_media, old_get_catalogs_dir_path, old_remove_catalog_media, old_add_catalog_media_file, old_add_product_media_file, old_get_catalog_album_builder, old_get_product_album_builder, old_get_products_dir_path, old_make_product_media_dir, add_catalog_media_file, add_product_media_file, get_catalog_album_builder, get_product_album_builder
import os

import pytz



async def permanent_mailing_task(bot: Bot):
    #print("per_mail")
    conn = await asyncpg.connect(**connection_params)

    overdue_mailings = await conn.fetch("SELECT id, catalog_id, next_mailing_date, mailing_interval FROM mailing_buffer WHERE next_mailing_date < $1", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))))
    
    for mailing in overdue_mailings:
        catalog = await conn.fetchrow("SELECT id, name, owner_id FROM catalogs WHERE id = $1", mailing["catalog_id"])
        owner_info = await conn.fetchrow("SELECT id, role, tg_user_id FROM accounts WHERE id = $1", catalog["owner_id"])
        owner_tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = True", owner_info["id"])

        if owner_info["role"] == "user":
            await catalog_mailing(owner_tariff, owner_info["tg_user_id"], owner_info["id"], catalog["id"], conn, bot, catalog["name"])
        elif owner_info["role"] == "admin":
            await admin_catalog_mailing(owner_info["id"], catalog["id"], conn, bot, catalog["name"])

        print("Mailing finished. Changing next m. date. Catalog id: " + str(mailing["catalog_id"]))

        mailing_interval = mailing["mailing_interval"]
        if mailing["next_mailing_date"] + mailing_interval < datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))):
            await conn.execute("UPDATE mailing_buffer SET next_mailing_date = $1 WHERE id = $2", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))) + mailing_interval, mailing["id"])
        else: 
            await conn.execute("UPDATE mailing_buffer SET next_mailing_date = $1 WHERE id = $2", mailing["next_mailing_date"] + mailing_interval, mailing["id"])
        
    await conn.close()


async def catalog_mailing(sender_tariff, sender_tg_id, sender_id, catalog_id, conn, bot: Bot, catalog_name: str):
    #print("catalog_mailing")
    next_line = await conn.fetch("SELECT id, tg_user_id, language_code, referer_id FROM accounts WHERE referer_id = $1", sender_id)
    product_list = await conn.fetch("SELECT name, id FROM products WHERE catalog_id = $1", catalog_id)
    #!!!!!
    # await bot.send_message(chat_id=sender_id, text="test", reply_markup=received_products_in_catalog_menu_kb(product_list, "en"))

    #next_line = await conn.fetch("SELECT id, tg_user_id, language_code, referer_id FROM accounts WHERE id = $1", sender_id)
    mailing_line_count = await conn.fetchval("SELECT mailing_line_count FROM tariff_params WHERE tariff = $1", sender_tariff)
    receivers = []
    await complect_receivers(next_line, conn, receivers, 1, mailing_line_count)
    #await complect_receivers(next_line, conn, receivers, 0, mailing_line_count)
    TRANSMIT_BY_INHERITANCE_TARIFFS = (await conn.fetchval("SELECT TRANSMIT_BY_INHERITANCE_TARIFFS FROM config LIMIT 1")).split(",")
    for receiver_dict in receivers:
        receiver = receiver_dict["receiver"]
        reciever_line_number = receiver_dict["line_number"]

        receiver_tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", receiver["id"])
        mailing_off_lines_count = await conn.fetchval("SELECT mailing_off_lines_count FROM tariff_params WHERE tariff = $1", receiver_tariff)

        receiver_referer_tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", receiver["referer_id"])
        referer_mailing_off_lines_count = await conn.fetchval("SELECT mailing_off_lines_count FROM tariff_params WHERE tariff = $1", receiver_referer_tariff)
        
        if receiver_tariff == "base" or sender_tariff != "base":
            if receiver_referer_tariff in TRANSMIT_BY_INHERITANCE_TARIFFS:
                if referer_mailing_off_lines_count == None or mailing_off_lines_count < referer_mailing_off_lines_count:
                    mailing_off_lines_count = referer_mailing_off_lines_count
            if mailing_off_lines_count != None and reciever_line_number > mailing_off_lines_count: 
                if receiver["tg_user_id"] != None:
                    lang_code = receiver["language_code"]
                    # text = languages[lang_code]["texts"]["mailing_text"]["text"] + str(sender_tg_id) + "\n"
                    # text += languages[lang_code]["texts"]["catalog_text"]["catalog"] + catalog_name + ":"
                    # try:
                    #     #await bot.send_message(chat_id=receiver["tg_user_id"], text=text, reply_markup=received_catalog_kb(catalog_id, catalog_name, lang_code))
                    #     await bot.send_message(chat_id=receiver["tg_user_id"], text=text, reply_markup=received_products_in_catalog_menu_kb(product_list, lang_code))
                    try:
                        await view_received_catalog_method(receiver["tg_user_id"], catalog_id, bot, False, lang_code)
                    except Exception as e:
                        print(e)
                        print(e.__traceback__)
                        
async def admin_catalog_mailing(admin_id, catalog_id, conn, bot: Bot, catalog_name: str):
    #print("admin_catalog_mailing")
    receivers = await conn.fetch("SELECT id, tg_user_id, language_code FROM accounts WHERE tg_user_id IS NOT NULL AND role = 'user'")
    product_list = await conn.fetch("SELECT name, id FROM products WHERE catalog_id = $1", catalog_id)
    #!!!!
    # await bot.send_message(chat_id=await conn.fetchval("SELECT tg_user_id FROM accounts WHERE id = $1", admin_id), 
    #                        text="test", reply_markup=received_products_in_catalog_menu_kb(product_list, "en"))

    for receiver in receivers:
        tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", receiver["id"])
        admin_mailing_catalog_count = await conn.fetchval("SELECT admin_mailing_catalog_count FROM tariff_params WHERE tariff = $1", tariff)

        if admin_mailing_catalog_count == None or admin_mailing_catalog_count > 0: 
            limit_catalogs = await conn.fetch("SELECT id FROM catalogs WHERE owner_id = $1 ORDER BY id LIMIT $2", admin_id, admin_mailing_catalog_count)
            limit_catalogs_ids = [catalog["id"] for catalog in limit_catalogs]
            if admin_mailing_catalog_count == None or catalog_id in limit_catalogs_ids:
                lang_code = receiver["language_code"]
                # text = languages[lang_code]["texts"]["mailing_text"]["admin_text"] + "\n"
                # text += languages[lang_code]["texts"]["catalog_text"]["catalog"] + catalog_name + ":"
                # try:
                #     await bot.send_message(chat_id=receiver["tg_user_id"], text=text, reply_markup=received_products_in_catalog_menu_kb(product_list, lang_code))
                try:
                    await view_received_catalog_method(receiver["tg_user_id"], catalog_id, bot, False, lang_code)
                except Exception as e:
                    print(e)
                    print(e.__traceback__)
    

#------------

async def complect_receivers(line: list, conn, receiver_list: list, line_number: int, max_line) -> list:
    next_line = []
    for receiver in line:
        receiver_list.append({"receiver": receiver, "line_number": line_number})
        subreceivers = await conn.fetch("SELECT id, tg_user_id, language_code, referer_id FROM accounts WHERE referer_id = $1", receiver["id"])
        for subreceiver in subreceivers:
            next_line.append(subreceiver)
    if next_line != [] and line_number < max_line:
        await complect_receivers(next_line, conn, receiver_list, line_number + 1, max_line)


#-----------
        
async def view_received_catalog_method(chat_id, catalog_id: int, bot: Bot, add_to_buffer: bool, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    
    products = await conn.fetch("SELECT id, name FROM products WHERE catalog_id = $1", catalog_id)
    catalog_info = await conn.fetchrow("SELECT name, owner_id FROM catalogs WHERE id = $1", catalog_id)
    owner_info = await conn.fetchrow("SELECT id, tg_user_id, role, login FROM accounts WHERE id = $1", catalog_info["owner_id"])

    reply_markup = received_products_in_catalog_menu_kb(products, lang_code)

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
        group = await bot.send_media_group(chat_id=chat_id, media=media)

    for mess in group:
        messages_to_wait.append(mess)

    text = None
    if owner_info["role"] == "user":
        #text = languages[lang_code]["texts"]["mailing_text"]["text"] + str(owner_info["tg_user_id"]) + "\n"
        text = languages[lang_code]["texts"]["mailing_text"]["text"] + str(owner_info["login"]) + "\n"
    else:
        text = languages[lang_code]["texts"]["mailing_text"]["admin_text"] + "\n"
    text += languages[lang_code]["texts"]["catalog_text"]["catalog"] + catalog_info["name"] + ":"

    cbck_mess = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
      
    if add_to_buffer == True:
        messages_to_wait.append(cbck_mess)

    for mess in messages_to_wait:
        await add_to_waiting_cbck_buffer(conn, mess)

    await conn.close()
    

async def rm_catalog_from_publication(catalog_id: int, conn):
    await conn.execute("DELETE FROM mailing_buffer WHERE catalog_id = $1", catalog_id)
    await conn.execute("UPDATE catalogs SET status = 'not_published' WHERE id = $1", catalog_id)
    