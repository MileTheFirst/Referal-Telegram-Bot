from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb, cancel_inline_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.tariff_kbs import tariffs_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from Utils.Keyboards.catalogs_products_kbs import my_catalogs_menu_kb, my_product_menu_kb, products_menu_kb
from Utils.Keyboards.cat_kbs import cats_in_cat_builder
from States.auth_states import InvitedRegForm
from States.search_states import SearchProductsFilterForm
from Filters.filters import CallbackArgFilter
from aiogram.utils.media_group import MediaGroupBuilder
from Utils.Methods.complect_ref_stat import complect_ref_stat

from Utils.Methods.mailing import permanent_mailing_task
from Utils.Methods.tariff_upd import permanent_tariff_update_task
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Utils.Methods.cats import complect_subcats
from Sources.files import languages

from Sources.files import set_last_tariff_check_date

import os

from datetime import datetime


search_router = Router()

search_router.message.filter(MagicData(F.is_auth.is_(True)))
search_router.callback_query.filter(MagicData(F.is_auth.is_(True)))

@search_router.callback_query(F.data == "cancel_search_products")
async def cancel_search_product(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    try: 
        await state.clear()
        await query.message.edit_text(languages[lang_code]["answers"]["search_router"]["cancel"]["search_products"])
        await query.message.edit_reply_markup(reply_markup=back_kb("main_menu", lang_code))
    except Exception as e:
        print(e)
        print(e.__traceback__)
    finally:
        await conn.close()


@search_router.callback_query(F.data == "search_products")
async def find_product_start(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    try: 
        acc_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
        tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = True", acc_id)
        if tariff != "base":
            await state.set_state(SearchProductsFilterForm.search_products_category)
            builder = InlineKeyboardBuilder()
            builder.button(text=languages[lang_code]["keyboards"]["often"]["continue"], callback_data="view_cat!" + str(None) + "!main_cat")
            builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_search_products")
            builder.adjust(1)
            
            await query.message.edit_text(languages[lang_code]["answers"]["menus"]["menu"])
            await query.message.edit_reply_markup(reply_markup=builder.as_markup())
        else:
            await query.message.edit_text(languages[lang_code]["answers"]["search_router"]["base_tariff"])
            await query.message.edit_reply_markup(reply_markup=back_kb("main_menu", lang_code))
    except Exception as e:
        print(e)
        print(e.__traceback__)
    finally:
        await conn.close()

@search_router.callback_query(SearchProductsFilterForm.search_products_result, CallbackArgFilter("choose_cat"))
@search_router.callback_query(SearchProductsFilterForm.search_products_category, CallbackArgFilter("choose_cat"))
async def choose_product_cat(query: CallbackQuery, state: FSMContext, lang_code: str):
    split = query.data.split("!")
    cat_id = None
    if split[1] != "None":
        cat_id = int(split[1])
    cat_name = split[2]
    conn = await asyncpg.connect(**connection_params)

    text = languages[lang_code]["answers"]["special_router"]["chose_search_cat"] 
    
    await state.update_data({"cat_id": cat_id})
    await state.update_data({"cat_name": cat_name})
    await state.set_state(SearchProductsFilterForm.search_products_query)
    cbck_message = await query.message.answer(text=text + cat_name + "\n" + languages[lang_code]["answers"]["search_router"]["write_query"], reply_markup=cancel_inline_kb("cancel_search_products", lang_code))

    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)
    await conn.close()


@search_router.message(SearchProductsFilterForm.search_products_query, F.text)
@search_router.callback_query(SearchProductsFilterForm.search_products_result, F.data == "search_results")
async def search_product_result(query: Message | CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    data = await state.get_data()
    
    search_query: str = None
    if isinstance(query, Message):
        search_query = query.text
    else:
        search_query = data["search_query"]

    # query_lang, confidence = langid.classify(search_query)
    # print(query_lang)
    #print(data["cat_id"])
    #print(type(data["cat_id"]))
    if data["cat_id"] == None:
        cat_line = await conn.fetch("SELECT id FROM categories WHERE parent_cat_id IS NULL")
        #print("Subcats:>")
        #print(cat_line)
    else:
        cat_line = await conn.fetch("SELECT id FROM categories WHERE id = $1", data["cat_id"])
    #print(cat_line)
    cat_list = []
    #cat_list += cat_line
    await complect_subcats(cat_line, conn, cat_list)
    #print(cat_list)

    # search_query = search_query.replace(" ", "% & ")
    # search_query += "%"
    search_query = search_query.replace(" ", "% |")
    search_query += "%"

    #print(search_query)
    #MIN_SEARCH_SIMILARITY = await conn.fetchval("SELECT MIN_SEARCH_SIMILARITY FROM config LIMIT 1")

    # products = await conn.fetch(''' 
    #     SELECT * FROM products
    #     WHERE 
    #         similarity(description, $1) > $2 AND category_id = ANY($3)
    #     ORDER BY 
    #         similarity(description, $1) DESC;
    # ''', search_query, MIN_SEARCH_SIMILARITY, cat_list)

    # products = await conn.fetch(''' 
    #     SELECT *, ts_rank(to_tsvector('english', description), to_tsquery('english', $1)) AS rank FROM products
    #     WHERE 
    #         to_tsvector('english', description) @@ to_tsquery('english', $1) AND category_id = ANY($2)
    #     ORDER BY 
    #         rank DESC;
    # ''', search_query, cat_list)

    # products = await conn.fetch(''' 
    #     SELECT *, ts_rank(to_tsvector(description), to_tsquery($1)) AS rank FROM products
    #     WHERE 
    #         to_tsvector(description) @@ to_tsquery($1) AND category_id = ANY($2)
    #     ORDER BY 
    #         rank DESC;
    # ''', search_query, cat_list)

    search_results_limit = await conn.fetchval("SELECT SEARCH_RESULTS_LIMIT FROM config LIMIT 1")

    products = await conn.fetch(''' 
        SELECT *, ts_rank(tsvector_desc, to_tsquery($1)) AS rank FROM products
        WHERE 
            tsvector_desc @@ to_tsquery($1) AND category_id = ANY($2) AND (SELECT status FROM catalogs WHERE id = catalog_id) = 'published'
        ORDER BY 
            rank DESC
        LIMIT $3;
    ''', search_query, cat_list, search_results_limit)

    #similarity(description, $1) > 0.001 AND 

    text = languages[lang_code]["answers"]["search_router"]["found_products"]
    #print(products)
    
    if isinstance(query, Message):
        #print("message")
        cbck_mess = await query.answer(text=text, reply_markup=products_menu_kb(products, lang_code, "choose_cat!" + str(data["cat_id"]) + "!" + data["cat_name"], "cancel_search_products"))
        await state.update_data({"search_query": search_query})
        await state.set_state(SearchProductsFilterForm.search_products_result)
        await add_to_waiting_cbck_buffer(conn, cbck_mess)
    elif isinstance(query, CallbackQuery): 
        #print("callback_query")
        await query.message.edit_text(text)
        await query.message.edit_reply_markup(reply_markup=products_menu_kb(products, lang_code, "choose_cat!" + str(data["cat_id"]) + "!" + data["cat_name"], "cancel_search_products"))

    await conn.close()