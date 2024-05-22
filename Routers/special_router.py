from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile, ChatMemberUpdated
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, MEMBER, KICKED
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb, edit_kb, cancel_inline_kb, del_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.cat_kbs import cats_in_cat_builder, choose_cat_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from States.manage_states import AddCatalogForm, DelCatalogForm, AddProductForm, EditProductForm
from States.search_states import SearchProductsFilterForm
from Filters.filters import CallbackArgFilter, StatesFilter, RoleFilter
from Sources.files import remove_product_media_dir, old_get_products_dir_path, remove_product_media_dir, old_make_product_media_dir
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Sources.files import languages
#from Sources.files import s3
from Utils.Methods.mailing import rm_catalog_from_publication

import os

special_router = Router()

special_router.message.filter(MagicData(F.is_auth.is_(True)))
special_router.callback_query.filter(MagicData(F.is_auth.is_(True)))

special_router.my_chat_member.filter(MagicData(F.is_auth.is_(True)))


@special_router.callback_query(SearchProductsFilterForm.search_products_category, CallbackArgFilter("view_cat"))
@special_router.callback_query(EditProductForm.edit_product_cat, CallbackArgFilter("view_cat"))
@special_router.callback_query(AddProductForm.add_product_cat, CallbackArgFilter("view_cat"))
async def add_product_cat(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    split = query.data.split("!")
    cat_name = split[2]
    cat_id = None

    if split[1] != "None":
        cat_id = int(split[1])
        categories = await conn.fetch("SELECT id, name FROM categories WHERE parent_cat_id = $1", cat_id)
    else:
        categories = await conn.fetch("SELECT id, name FROM categories WHERE parent_cat_id IS NULL")
    #print(categories)

    parent_cat_id = None
    parent_cat_name = None
    if cat_id != None:
        parent_cat_id = await conn.fetchval("SELECT parent_cat_id FROM categories WHERE id = $1", cat_id)
        parent_cat_name = "main_cat"
        if parent_cat_id != None:
            parent_cat_name = await conn.fetchval("SELECT name FROM categories WHERE id = $1", parent_cat_id)

    builder = InlineKeyboardBuilder()
    if categories != []:
        builder = cats_in_cat_builder(categories, lang_code)

    state_now = await state.get_state()
    
    if categories == [] or state_now == SearchProductsFilterForm.search_products_category:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["choose"], callback_data="choose_cat!"+str(cat_id) + "!" + cat_name)
        
    if cat_id != None:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="view_cat!" + str(parent_cat_id) + "!" + parent_cat_name)

    if state_now == AddProductForm.add_product_cat.state:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_add_product")
    elif state_now == SearchProductsFilterForm.search_products_category:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_search_products")
    else:
        data = await state.get_data()
        product_id = data["product_id"]
        builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_edit_product!"+str(product_id))

    builder.adjust(1)
    if state_now == SearchProductsFilterForm.search_products_category:
        await query.message.edit_text(languages[lang_code]["answers"]["special_router"]["choose_search_cat"] + languages[lang_code]["words"]["categories"][cat_name])
    else:
        await query.message.edit_text(languages[lang_code]["answers"]["special_router"]["choose_cat"] + languages[lang_code]["words"]["categories"][cat_name])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()

@special_router.callback_query(EditProductForm.edit_product_cat, CallbackArgFilter("choose_cat"))
@special_router.callback_query(AddProductForm.add_product_cat, CallbackArgFilter("choose_cat"))
async def choose_product_cat(query: CallbackQuery, state: FSMContext, lang_code: str):
    split = query.data.split("!")
    cat_id = int(split[1])
    cat_name = split[2]
    conn = await asyncpg.connect(**connection_params)

    cbck_message = None

    text = languages[lang_code]["answers"]["special_router"]["chose_cat"] 
    if await state.get_state() == AddProductForm.add_product_cat.state:
        await state.update_data({"cat_id": cat_id})
        await state.set_state(AddProductForm.add_product_name)
        cbck_message = await query.message.answer(text=text + languages[lang_code]["words"]["categories"][cat_name] + "\n" + languages[lang_code]["answers"]["manage_product_router"]["add_product"]["write_name"], reply_markup=cancel_inline_kb("cancel_add_product", lang_code))
    else:
        data = await state.get_data()
        product_id = data["product_id"]
        await conn.execute("UPDATE products SET category_id = $1 WHERE id = $2", cat_id, product_id)

        catalog_id = await conn.fetchval("SELECT catalog_id FROM products WHERE id = $1", product_id)
        await rm_catalog_from_publication(catalog_id, conn)
        
        cbck_message = await query.message.answer(text=text + languages[lang_code]["words"]["categories"][cat_name], reply_markup=back_kb("edit_product!"+str(product_id), lang_code))
        await state.clear()

    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)
    await conn.close()


@special_router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED), RoleFilter("user"))
async def user_blocked_bot(event: ChatMemberUpdated):
    conn = await asyncpg.connect(**connection_params)

    await conn.execute("UPDATE accounts SET blocking = 'bot_kicked' WHERE tg_user_id = $1", event.from_user.id)

    await conn.close()

@special_router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER), RoleFilter("user"))
async def user_blocked_bot(event: ChatMemberUpdated):
    conn = await asyncpg.connect(**connection_params)

    user_info = await conn.fetchrow("SELECT blocking FROM accounts WHERE tg_user_id = $1", event.from_user.id)

    if user_info["blocking"] == "bot_kicked":
        await conn.execute("UPDATE accounts SET blocking = NULL WHERE tg_user_id = $1", event.from_user.id)
        await event.answer("Bot was ublocked")

    await conn.close()


#---------------------------



# @special_router.callback_query(SearchProductsFilterForm.search_products_category, CallbackArgFilter("view_cat"))
# async def search_product_cat(query: CallbackQuery, state: FSMContext, lang_code: str):
#     conn = await asyncpg.connect(**connection_params)

#     split = query.data.split("!")
#     cat_name = split[2]
#     cat_id = None

#     if split[1] != "None":
#         cat_id = int(split[1])
#         categories = await conn.fetch("SELECT id, name FROM categories WHERE parent_cat_id = $1", cat_id)
#     else:
#         categories = await conn.fetch("SELECT id, name FROM categories WHERE parent_cat_id IS NULL")
#     #print(categories)

#     parent_cat_id = None
#     parent_cat_name = None
#     if cat_id != None:
#         parent_cat_id = await conn.fetchval("SELECT parent_cat_id FROM categories WHERE id = $1", cat_id)
#         parent_cat_name = "main_cat"
#         if parent_cat_id != None:
#             parent_cat_name = await conn.fetchval("SELECT name FROM categories WHERE id = $1", parent_cat_id)

#     builder = InlineKeyboardBuilder()
#     if categories != []:
#         builder = cats_in_cat_builder(categories)
    
#     builder.button(text=languages[lang_code]["keyboards"]["often"]["choose"], callback_data="choose_cat!"+str(cat_id) + "!" + cat_name)
        
#     if cat_id != None:
#         builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="view_cat!" + str(parent_cat_id) + "!" + parent_cat_name)
#     builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_search_products")

#     builder.adjust(1)
#     await query.message.edit_text(languages[lang_code]["answers"]["search_router"]["choose_cat"] + cat_name)
#     await query.message.edit_reply_markup(reply_markup=builder.as_markup())

#     await conn.close()

