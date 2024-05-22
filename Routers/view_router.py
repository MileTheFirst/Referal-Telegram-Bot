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
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from Utils.Keyboards.catalogs_products_kbs import products_menu_kb, product_menu_kb, my_product_menu_kb, received_products_in_catalog_menu_kb, received_product_menu_kb
from States.auth_states import InvitedRegForm
from Filters.filters import CallbackArgFilter
from aiogram.utils.media_group import MediaGroupBuilder
from Utils.Methods.complect_ref_stat import complect_ref_stat
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Utils.Methods.mailing import view_received_catalog_method
from Sources.files import languages
from Sources.files import remove_product_media_dir, old_remove_product_media_dir, remove_catalog_media, old_get_catalogs_dir_path, old_remove_catalog_media, old_add_catalog_media_file, old_add_product_media_file, old_get_catalog_album_builder, old_get_product_album_builder, old_get_products_dir_path, old_make_product_media_dir, add_catalog_media_file, add_product_media_file, get_catalog_album_builder, get_product_album_builder
from Sources.files import s3
from datetime import timedelta, datetime

import os

view_router = Router()

view_router.message.filter(MagicData(F.is_auth.is_(True)))
view_router.callback_query.filter(MagicData(F.is_auth.is_(True)))

# @view_router.callback_query(CallbackArgFilter("view_catalog"))
# async def view_catalog(query: CallbackQuery, lang_code: str):
#     conn = await asyncpg.connect(**connection_params)
#     catalog_id = int(query.data.split("!")[1])
#     products = await conn.fetch("SELECT id, name FROM products WHERE catalog_id = $1", catalog_id)
#     catalog_info = await conn.fetchrow("SELECT name, owner_id FROM catalogs WHERE id = $1", catalog_id)

#     reply_markup = products_menu_kb(products, lang_code) #back_data .............

#     text = languages[lang_code]["texts"]["catalog_text"]["catalog"] + catalog_info['name'] + ":"
#     cbck_message = await query.message.answer(text=text, reply_markup=reply_markup)
#     await add_to_waiting_cbck_buffer(conn, cbck_message)
#     await query.message.delete()
#     await del_from_waiting_cbck_buffer(conn, query.message)

#     await conn.close()

@view_router.callback_query(CallbackArgFilter("view_my_catalog"))
async def view_catalog(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])
    products = await conn.fetch("SELECT id, name FROM products WHERE catalog_id = $1", catalog_id)
    catalog_info = await conn.fetchrow("SELECT name, owner_id, status FROM catalogs WHERE id = $1", catalog_id)
    user_info = await conn.fetchrow("SELECT role FROM accounts WHERE id = $1", catalog_info["owner_id"])

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
        builder.button(text=product["name"], callback_data= "view_my_product!" + str(product["id"]))
    builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["add_product"], callback_data="add_product!"+str(catalog_id))
    builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["edit_photo"], callback_data="edit_catalog_photo!"+str(catalog_id))

    if catalog_info["status"] == "approved":
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["publish"], callback_data="publish_catalog!"+ str(catalog_id))
    elif catalog_info["status"] == "not_published" and user_info["role"] != "admin": 
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["send_to_mod"], callback_data="send_to_moderation_catalog!" + str(catalog_id))
    elif catalog_info["status"] == "under_moderation":
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["rm_from_mod"], callback_data="rm_from_moderation_catalog!" + str(catalog_id))
    elif catalog_info["status"] == "published":
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["edit_catalog_next_mailing_date"], callback_data="edit_catalog_next_mailing_date!"+str(catalog_id))
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["edit_catalog_mailing_interval"], callback_data="edit_catalog_mailing_interval!"+str(catalog_id))
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["rm_from_pub"], callback_data="rm_from_publication_catalog!" + str(catalog_id))
    elif user_info["role"] == "admin":
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["publish"], callback_data="publish_catalog!"+ str(catalog_id))

    if catalog_info["status"] != "rejected":
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["del_catalog"], callback_data="del_catalog!"+str(catalog_id))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="my_catalogs")
    builder.adjust(1)

    text = languages[lang_code]["texts"]["catalog_text"]["status"] + languages[lang_code]["texts"]["statuses"][catalog_info["status"]] + "\n"
    if catalog_info["status"] == "published":
        mailing_info = await conn.fetchrow("SELECT * FROM mailing_buffer WHERE catalog_id = $1", catalog_id)
        text += languages[lang_code]["texts"]["catalog_text"]["next_mailing_date"] + " (UTC+3) " + mailing_info["next_mailing_date"].strftime("%Y-%m-%d %H:%M") + "\n"
        mailing_interval: timedelta = mailing_info["mailing_interval"]
        text += languages[lang_code]["texts"]["catalog_text"]["mailing_interval"] 
        text += str(mailing_interval.days) + languages[lang_code]["texts"]["date_text"]["days"] + str(mailing_interval.seconds // 3600) + languages[lang_code]["texts"]["date_text"]["hours"] + str((mailing_interval.seconds // 60) % 60) + languages[lang_code]["texts"]["date_text"]["mins"] + "\n"

    text += languages[lang_code]["texts"]["catalog_text"]["catalog"] + catalog_info['name'] + ":"

    messages_to_wait.append(await query.message.answer(text=text, reply_markup=builder.as_markup()))

    for mess in messages_to_wait:
        await add_to_waiting_cbck_buffer(conn, mess)

    await delete_cbck_message(conn, query.message)

    await conn.close()


@view_router.callback_query(CallbackArgFilter("view_received_catalog"))
async def view_received_catalog(query: CallbackQuery, bot: Bot, lang_code: str):
    catalog_id = int(query.data.split("!")[1])
    await view_received_catalog_method(query.from_user.id, catalog_id, bot, False, lang_code)
    await query.message.delete()
    

#--------------------------------------------



@view_router.callback_query(CallbackArgFilter("view_product"))
@view_router.callback_query(CallbackArgFilter("view_my_product"))
@view_router.callback_query(CallbackArgFilter("view_received_product"))
@view_router.callback_query(CallbackArgFilter("view_moderating_product"))
async def view_my_product(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    cbck_arg = query.data.split("!")[0]

    product_id = int(query.data.split("!")[1])
    
    product_info = await conn.fetchrow("SELECT name, description, catalog_id, category_id FROM products WHERE id = $1", product_id)
    cat_name = await conn.fetchval("SELECT name FROM categories WHERE id = $1", product_info["category_id"])

    messages_to_wait = []

    #languages[lang_code]["texts"]["product_text"]["name"] + ": " + product_info["name"]

    ####
    album_builder = get_product_album_builder(product_id)
    ####
    ####
    # album_builder = old_get_product_album_builder(product_id)
    ####
    
    media=album_builder.build()
    group = []
    if media != []:
        group = await query.message.answer_media_group(media=media)

    for mess in group:
        messages_to_wait.append(mess)

    text = languages[lang_code]["texts"]["product_text"]["name"] + product_info["name"] + "\n"
    text += languages[lang_code]["texts"]["product_text"]["cat"] + languages[lang_code]["words"]["categories"][cat_name] + "\n"
    text += languages[lang_code]["texts"]["product_text"]["desc"] + product_info["description"]

    messages_to_wait.append(await query.message.answer(text=text))

    reply_markup = None
    if cbck_arg == "view_product":
        #back_data = query.data.split("!")[2]
        reply_markup = back_kb("search_results", lang_code)
    elif cbck_arg == "view_my_product":
        reply_markup = my_product_menu_kb(product_id, product_info["catalog_id"], lang_code)
    elif cbck_arg == "view_received_product":
        reply_markup = back_kb("view_received_catalog!" + str(product_info["catalog_id"]),  lang_code)
    elif cbck_arg == "view_moderating_product":
        reply_markup = back_kb("moderate_catalog!" + str(product_info["catalog_id"]), lang_code)
    
    menu_mess = await query.message.answer(languages[lang_code]["answers"]["view_router"]["product_menu"], reply_markup=reply_markup)
    if cbck_arg != "view_received_product":
        messages_to_wait.append(menu_mess)
        
    for mess in messages_to_wait:
        await add_to_waiting_cbck_buffer(conn, mess)

    await delete_cbck_message(conn, query.message)
    
    await conn.close()