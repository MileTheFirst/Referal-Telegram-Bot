from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
from Sources.files import s3
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb, cancel_inline_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from Utils.Keyboards.catalogs_products_kbs import received_products_in_catalog_menu_kb
from States.manage_states import AddCatalogForm, DelCatalogForm, EditMailingForm, EditCatalogForm
from Filters.filters import CallbackArgFilter, StatesFilter, RoleFilter
from Sources.files import remove_product_media_dir, old_remove_product_media_dir, remove_catalog_media, old_get_catalogs_dir_path, old_remove_catalog_media, old_add_catalog_media_file, old_add_product_media_file, old_get_catalog_album_builder, old_get_product_album_builder, old_get_products_dir_path, old_make_product_media_dir, add_catalog_media_file, add_product_media_file, get_catalog_album_builder, get_product_album_builder
from Utils.Methods.mailing import catalog_mailing
from Utils.Methods.mailing import rm_catalog_from_publication
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Sources.files import languages
from Utils.Methods.moderation import find_free_moderator

import os

from datetime import datetime, timedelta, timezone

import pytz




manage_catalog_router = Router()

manage_catalog_router.message.filter(MagicData(F.is_auth.is_(True)))
manage_catalog_router.callback_query.filter(MagicData(F.is_auth.is_(True)))

@manage_catalog_router.callback_query(F.data == "cancel_add_catalog")
async def cancel_adding_catalog(query: CallbackQuery, state: FSMContext, lang_code: str):
    await state.clear()
    await query.message.edit_text(text=languages[lang_code]["answers"]["manage_catalog_router"]["cancel"]["adding_catalog"])
    await query.message.edit_reply_markup(reply_markup=back_kb("my_catalogs", lang_code))

@manage_catalog_router.callback_query(F.data == "cancel_edit_mailing")
async def cancel_adding_catalog(query: CallbackQuery, state: FSMContext, lang_code: str):
    data = await state.get_data()
    await state.clear()
    await query.message.edit_text(text=languages[lang_code]["answers"]["manage_catalog_router"]["cancel"]["edit_mailing"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!" + str(data["catalog_id"]), lang_code))
    
@manage_catalog_router.callback_query(F.data == "cancel_edit_catalog_photo")
async def cancel_adding_catalog(query: CallbackQuery, state: FSMContext, lang_code: str):
    data = await state.get_data()
    await state.clear()
    await query.message.edit_text(text=languages[lang_code]["answers"]["manage_catalog_router"]["cancel"]["edit_photo"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!" + str(data["catalog_id"]), lang_code))



@manage_catalog_router.callback_query(F.data == "add_catalog")
async def add_catalog(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    user_info = await conn.fetchrow("SELECT id, blocking FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", user_info["id"])
    max_own_catalog_count = await conn.fetchval("SELECT max_own_catalog_count FROM tariff_params WHERE tariff = $1", tariff)
    own_catalog_count = await conn.fetchval("SELECT count(*) FROM catalogs WHERE owner_id = $1", user_info["id"])

    if user_info["blocking"] == None:
        if max_own_catalog_count == None or own_catalog_count < max_own_catalog_count:
            await state.update_data({"owner_id": user_info["id"]})
            await state.set_state(AddCatalogForm.add_catalog_name)

            cbck_message = await query.message.answer(text=languages[lang_code]["answers"]["manage_catalog_router"]["add_write_name"], reply_markup=cancel_inline_kb("cancel_add_catalog", lang_code))
            await delete_cbck_message(conn, query.message)
            await add_to_waiting_cbck_buffer(conn, cbck_message)
        else: 
            text = languages[lang_code]["answers"]["manage_catalog_router"]["not_correct"]["add_catalog_1"] + str(max_own_catalog_count)
            text += languages[lang_code]["answers"]["manage_catalog_router"]["not_correct"]["add_catalog_2"]
            await query.message.edit_text(text)

            builder = InlineKeyboardBuilder()
            builder.button(text=languages[lang_code]["keyboards"]["user_router"]["user_main_menu"]["tariffs"],  callback_data="tariffs")
            builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="my_catalogs")
            builder.adjust(1)
    
            await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    else:
        text = None
        if user_info["blocking"] == "blocked":
            text = languages[lang_code]["answers"]["blocked"]
        elif user_info["blocking"] == "waiting_attach":
            text = languages[lang_code]["answers"]["blocked_w_a"]

        await query.message.edit_text(text)
        await query.message.edit_reply_markup(reply_markup=back_kb("my_catalogs", lang_code))

    await conn.close()


@manage_catalog_router.message(AddCatalogForm.add_catalog_name, F.text)
async def catalog_name_and_adding(message: Message, state: FSMContext, lang_code: str):
    catalog_name = html.quote(message.text)
    if  len(catalog_name) > 2 and len(catalog_name) < 50:
        conn = await asyncpg.connect(**connection_params)
        data = await state.get_data()
        catalog_id = await conn.fetchval("INSERT INTO catalogs (name, owner_id, status) VALUES ($1, $2, 'not_published') RETURNING id", catalog_name, data["owner_id"])

        builder = InlineKeyboardBuilder()
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["add_product"], callback_data="add_product!"+str(catalog_id))
        builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_catalog_menu"]["edit_photo"], callback_data="edit_catalog_photo!"+str(catalog_id))
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="my_catalogs")
        builder.adjust(1)

        cbck_message = await message.answer(languages[lang_code]["answers"]["manage_catalog_router"]["catalog_added"], reply_markup=builder.as_markup())

        await add_to_waiting_cbck_buffer(conn, cbck_message)

        await state.clear()
        await conn.close()
    else: 
        await message.answer(text=languages[lang_code]["answers"]["manage_catalog_router"]["not_correct"]["name"])

@manage_catalog_router.callback_query(CallbackArgFilter("edit_catalog_photo"))
async def change_photo(query: CallbackQuery, state: FSMContext, lang_code: str):
    catalog_id = int(query.data.split("!")[1])
    conn = await asyncpg.connect(**connection_params)

    await state.set_state(EditCatalogForm.edit_catalog_photo)
    await state.update_data({"catalog_id": catalog_id})

    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["del"], callback_data="delete_catalog_photo")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_edit_catalog_photo")
    builder.adjust(1)

    cbck_mess = await query.message.answer(text=languages[lang_code]["answers"]["manage_catalog_router"]["edit_photo"], reply_markup=builder.as_markup())

    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@manage_catalog_router.callback_query(EditCatalogForm.edit_catalog_photo, F.data == "delete_catalog_photo")
@manage_catalog_router.message(EditCatalogForm.edit_catalog_photo, F.photo)
async def catalog_name_and_adding(update: Message | CallbackQuery, state: FSMContext, bot: Bot, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    data = await state.get_data()
    catalog_id = data["catalog_id"]

    ####
    remove_catalog_media(catalog_id)
    ####
    ####
    #old_remove_catalog_media(catalog_id)
    ####

    message = None
    if isinstance(update, Message):
        message = update
        photo = None
        MAX_PHOTO_SIZE = await conn.fetchval("SELECT MAX_PHOTO_SIZE FROM config LIMIT 1")
        for photo_size in reversed(message.photo):
            if photo_size.file_size < MAX_PHOTO_SIZE:
                photo = photo_size
                break

        ####
        await add_catalog_media_file(photo, catalog_id, bot)
        ####
        ####
        #await old_add_catalog_media_file(photo, catalog_id, bot)
        ####
    elif isinstance(update, CallbackQuery):
        message = update.message

    cbck_message = await message.answer(languages[lang_code]["answers"]["manage_catalog_router"]["photo_edited"], reply_markup=back_kb("view_my_catalog!"+str(catalog_id), lang_code))
    
    await rm_catalog_from_publication(catalog_id, conn)

    await add_to_waiting_cbck_buffer(conn, cbck_message)
    if isinstance(update, CallbackQuery):
        await delete_cbck_message(conn, message)

    await state.clear()
    await conn.close()
    

#--------------------------------------
        
#...........

#--------------------------------------

@manage_catalog_router.callback_query(CallbackArgFilter("del_catalog"))
async def catalog_deletting(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    catalog_id = int(query.data.split("!")[1])

    products = await conn.fetch("SELECT id FROM products WHERE catalog_id = $1", catalog_id)
    
    ####
    remove_catalog_media(catalog_id)
    ####
    ####
    #old_remove_catalog_media(catalog_id)
    ####
    for product in products:
        ####
        remove_product_media_dir(str(product["id"]))
        ####
        ####
        #old_remove_product_media_dir(str(product["id"]))
        ####
    await conn.execute("DELETE FROM products WHERE catalog_id = $1", catalog_id)
    await conn.execute("DELETE FROM mailing_buffer WHERE catalog_id = $1", catalog_id)
    await conn.execute("DELETE FROM moderation_list WHERE catalog_id = $1", catalog_id)
    #await conn.execute("DELETE FROM violation_list WHERE catalog_id = $1", catalog_id)
    await conn.execute("DELETE FROM catalogs WHERE id = $1", catalog_id)

    await state.clear()
    await query.message.edit_text(languages[lang_code]["answers"]["manage_catalog_router"]["catalog_deleted"])
    await query.message.edit_reply_markup(reply_markup=back_kb("my_catalogs", lang_code))



#------------
    

@manage_catalog_router.callback_query(CallbackArgFilter("send_to_moderation_catalog"))
async def send_to_moderation_catalog(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])

    pre_moderators = await conn.fetch("SELECT * FROM accounts WHERE role = 'support' and tg_user_id IS NOT NULL")

    moderator = await find_free_moderator(pre_moderators, conn)

    await conn.execute("INSERT INTO moderation_list (catalog_id, moderator_id) VALUES ($1, $2)", catalog_id, moderator["id"])
    await conn.execute("UPDATE catalogs SET status = 'under_moderation' WHERE id = $1", catalog_id)

    await query.message.edit_text(languages[lang_code]["answers"]["manage_catalog_router"]["catalog_sent_t_m"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!" + str(catalog_id), lang_code))

    await conn.close()


@manage_catalog_router.callback_query(CallbackArgFilter("publish_catalog"))
async def publish_catalog(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    try:
        catalog_id = int(query.data.split("!")[1])
        catalog_info = await conn.fetchrow("SELECT owner_id, name FROM catalogs WHERE id = $1", catalog_id)

        user_info = await conn.fetchrow("SELECT role, tg_user_id, id FROM accounts WHERE id = $1", catalog_info["owner_id"])
        
        tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", user_info["id"])
        tariff_info = await conn.fetchrow("SELECT * FROM tariff_params WHERE tariff = $1", tariff)
        if await conn.fetchval("SELECT COUNT(*) FROM mailing_buffer WHERE catalog_id = $1", catalog_id) == 0:
            if user_info["role"] == "user":
                await conn.execute("INSERT INTO mailing_buffer (catalog_id, next_mailing_date, mailing_interval) VALUES ($1, $2, $3)", catalog_id, datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))), tariff_info["mailing_interval"])
            else:
                DEFAULT_ADMIN_MAILING_INTERVAL_HOURS = await conn.fetchval("SELECT DEFAULT_ADMIN_MAILING_INTERVAL_HOURS FROM config LIMIT 1")
                await conn.execute("INSERT INTO mailing_buffer (catalog_id, next_mailing_date, mailing_interval) VALUES ($1, $2, $3)", catalog_id, datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))), timedelta(hours=DEFAULT_ADMIN_MAILING_INTERVAL_HOURS))

            await conn.execute("UPDATE catalogs SET status = 'published' WHERE id = $1", catalog_id)
            if tariff == "base":
                await query.message.edit_text(text=languages[lang_code]["answers"]["manage_catalog_router"]["publish_catalog_base"])
            else:
                await query.message.edit_text(text=languages[lang_code]["answers"]["manage_catalog_router"]["publish_catalog"])

            #####
            # text = None
            # if user_info["role"] == "user":
            #     text = languages[lang_code]["texts"]["mailing_text"]["text"] + str(user_info["tg_user_id"]) + "\n"
            # else:
            #     text = languages[lang_code]["texts"]["mailing_text"]["admin_text"] + "\n"
            # text += languages[lang_code]["texts"]["catalog_text"]["catalog"] + catalog_info["name"] + ":"
            # product_list = await conn.fetch("SELECT name, id FROM products WHERE catalog_id = $1", catalog_id)
            # await query.message.answer(text=text, reply_markup=received_products_in_catalog_menu_kb(product_list, lang_code))
            #####
        else: 
            raise Exception()
    except Exception as e:
        print(e)
        print(e.__traceback__)
        await query.message.edit_text(languages[lang_code]["answers"]["errors"]["smth"])
    finally:
        await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!"+str(catalog_id), lang_code))
        await conn.close()

@manage_catalog_router.callback_query(CallbackArgFilter("rm_from_moderation_catalog"))
async def rm_from_moderation_catalog(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])

    await conn.execute("DELETE FROM moderation_list WHERE catalog_id = $1", catalog_id)
    await rm_catalog_from_publication(catalog_id, conn)

    await query.message.edit_text(languages[lang_code]["answers"]["manage_catalog_router"]["rm_from_moderation_catalog"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!" + str(catalog_id), lang_code))

    await conn.close()

@manage_catalog_router.callback_query(CallbackArgFilter("rm_from_publication_catalog"))
async def rm_from_moderation_catalog(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])

    await conn.execute("DELETE FROM mailing_buffer WHERE catalog_id = $1", catalog_id)
    await conn.execute("UPDATE catalogs SET status = 'approved' WHERE id = $1", catalog_id)

    await query.message.edit_text(languages[lang_code]["answers"]["manage_catalog_router"]["rm_from_publication_catalog"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!" + str(catalog_id), lang_code))

    await conn.close()

@manage_catalog_router.callback_query(CallbackArgFilter("edit_catalog_mailing_interval"))
async def edit_catalog_mailing_interval(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])

    await state.update_data({"catalog_id": catalog_id})
    await state.set_state(EditMailingForm.edit_mailing_interval)

    text = languages[lang_code]["answers"]["manage_catalog_router"]["edit_mailing_interval"]
    cbck_message = await query.message.answer(text=text, reply_markup=cancel_inline_kb("cancel_edit_mailing", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)

    await delete_cbck_message(conn, query.message)

    await conn.close()

@manage_catalog_router.message(EditMailingForm.edit_mailing_interval, F.text)
async def publish_catalog(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    try:
        data = await state.get_data()
        catalog_id = data["catalog_id"]
        days = float(html.quote(message.text))

        user_info = await conn.fetchrow("SELECT role, id FROM accounts WHERE tg_user_id = $1", message.from_user.id)
        tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", user_info["id"])
        tariff_info = await conn.fetchrow("SELECT * FROM tariff_params WHERE tariff = $1", tariff)

        interval = timedelta(days=days)
        #print(interval)
        if tariff_info == None or interval >= tariff_info["mailing_interval"]:
            await conn.execute("UPDATE mailing_buffer SET mailing_interval = $1 WHERE catalog_id = $2", interval, catalog_id)
        else:
            raise Exception("Interval is less then available in tariff")
        
        cbck_message = await message.answer(text=languages[lang_code]["answers"]["manage_catalog_router"]["edited_mailing_interval"], reply_markup=back_kb("view_my_catalog!"+str(catalog_id), lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_message)
    except Exception as e:
        print(e)
        print(e.__traceback__)
        cbck_message = await message.answer(languages[lang_code]["answers"]["errors"]["smth_t_a"], reply_markup=cancel_inline_kb("cancel_edit_mailing", lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_message)
    finally:
        await state.clear()
        await conn.close()

#----------------------------------

@manage_catalog_router.callback_query(CallbackArgFilter("edit_catalog_next_mailing_date"))
async def edit_catalog_mailing_interval(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    catalog_id = int(query.data.split("!")[1])

    await state.update_data({"catalog_id": catalog_id})
    await state.set_state(EditMailingForm.edit_next_mailing_date)

    text = languages[lang_code]["answers"]["manage_catalog_router"]["edit_next_mailing_date"]
    cbck_message = await query.message.answer(text=text, reply_markup=cancel_inline_kb("cancel_edit_mailing", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)

    await delete_cbck_message(conn, query.message)

    await conn.close()

@manage_catalog_router.message(EditMailingForm.edit_next_mailing_date, F.text)
async def publish_catalog(message: Message, state: FSMContext, lang_code: str):
    try:
        conn = await asyncpg.connect(**connection_params)
        data = await state.get_data()
        catalog_id = data["catalog_id"]
        
        mess_text = html.quote(message.text)
        days = float(mess_text.split("%")[0])
        hours = float(mess_text.split("%")[1])
        

        user_info = await conn.fetchrow("SELECT role, id FROM accounts WHERE tg_user_id = $1", message.from_user.id)
        tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", user_info["id"])
        tariff_info = await conn.fetchrow("SELECT * FROM tariff_params WHERE tariff = $1", tariff)
        mailing_info = await conn.fetchrow("SELECT * FROM mailing_buffer WHERE catalog_id = $1", catalog_id)

        interval = timedelta(days=days, hours=hours)
        #print(interval)
        nowdate = datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS")))
        next_date = nowdate + interval
        if tariff_info == None or next_date >= mailing_info["next_mailing_date"] or next_date >= nowdate + tariff_info["mailing_interval"]:
            await conn.execute("UPDATE mailing_buffer SET next_mailing_date = $1 WHERE catalog_id = $2", next_date, catalog_id)
        else:
            raise Exception("Date is before available in tariff")
        
        cbck_message = await message.answer(text=languages[lang_code]["answers"]["manage_catalog_router"]["edited_next_mailing_date"], reply_markup=back_kb("view_my_catalog!"+str(catalog_id), lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_message)
    except Exception as e:
        print(e)
        print(e.__traceback__)
        cbck_message = await message.answer(languages[lang_code]["answers"]["errors"]["smth_t_a"], reply_markup=cancel_inline_kb("cancel_edit_mailing", lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_message)
    finally:
        await state.clear()
        await conn.close()
