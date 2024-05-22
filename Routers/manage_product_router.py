from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb, edit_kb, cancel_inline_kb, del_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.cat_kbs import cats_in_cat_builder, choose_cat_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from States.manage_states import AddCatalogForm, DelCatalogForm, AddProductForm, EditProductForm
from Filters.filters import CallbackArgFilter, StatesFilter
from Sources.files import remove_product_media_dir, old_remove_product_media_dir, remove_catalog_media, old_get_catalogs_dir_path, old_remove_catalog_media, old_add_catalog_media_file, old_add_product_media_file, old_get_catalog_album_builder, old_get_product_album_builder, old_get_products_dir_path, old_make_product_media_dir, add_catalog_media_file, add_product_media_file, get_catalog_album_builder, get_product_album_builder, delete_obj, delete_product_photo, get_product_objects, old_get_product_objects
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Sources.files import languages
from Sources.files import s3
from Utils.Methods.mailing import rm_catalog_from_publication
from Utils.Methods.db_methods import insert_into_products, update_product_desc

import os

manage_product_router = Router()

manage_product_router.message.filter(MagicData(F.is_auth.is_(True)))
manage_product_router.callback_query.filter(MagicData(F.is_auth.is_(True)))


# @manage_product_router.message(Command("cancel"), StatesFilter(AddProductForm.__all_states_names__))
# async def cancel_adding_catalog(message: Message, state: FSMContext, lang_code):
#     data = await state.get_data()
#     conn = await asyncpg.connect(**connection_params)
#     cbck_message = await message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["cancel"]["add_product"], reply_markup=back_kb("view_my_catalog!" + str(data["catalog_id"]), lang_code))
#     await add_to_waiting_cbck_buffer(conn, cbck_message)
#     await state.clear()
#     await conn.close()

@manage_product_router.callback_query(F.data == "cancel_add_product")
async def cancel_adding_catalog(query: CallbackQuery, state: FSMContext, lang_code: str):
    data = await state.get_data()
    conn = await asyncpg.connect(**connection_params)
    cbck_message = await query.message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["cancel"]["add_product"], reply_markup=back_kb("view_my_catalog!" + str(data["catalog_id"]), lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)
    await state.clear()
    await conn.close()

@manage_product_router.callback_query(CallbackArgFilter("cancel_edit_product"))
async def cancel_edit_product(query: CallbackQuery, state: FSMContext, lang_code: str):
    product_id = int(query.data.split("!")[1])
    conn = await asyncpg.connect(**connection_params)
    cbck_message = await query.message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["cancel"]["edit_product"], reply_markup=back_kb("view_my_product!" + str(product_id), lang_code))
    await state.clear()
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)
    await conn.close()




@manage_product_router.callback_query(CallbackArgFilter("add_product"))
async def add_product(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    user_info = await conn.fetchrow("SELECT id, blocking FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    tariff = await conn.fetchval("SELECT tariff FROM tariff_buffer WHERE user_id = $1 and is_active = true", user_info["id"])
    limits = await conn.fetchrow("SELECT max_own_product_count FROM tariff_params WHERE tariff = $1", tariff)
    catalogs = await conn.fetch("SELECT id FROM catalogs WHERE owner_id = $1", user_info["id"])
    own_catalogs = []
    for catalog in catalogs:
        own_catalogs.append(catalog["id"])
    own_product_count = await conn.fetchval("SELECT count(*) FROM products WHERE catalog_id = ANY($1)", own_catalogs)
    catalog_id = int(query.data.split("!")[1])

    if user_info["blocking"] == None:
        if limits == None or own_product_count < limits["max_own_product_count"]:
            await state.update_data({"owner_id": user_info["id"]})
            await state.update_data({"catalog_id": catalog_id})
            await state.set_state(AddProductForm.add_product_cat)

            await query.message.edit_text(text=languages[lang_code]["answers"]["menus"]["menu"])

            #builder = cats_in_cat_builder(categories)
            builder = InlineKeyboardBuilder()
            builder.button(text=languages[lang_code]["keyboards"]["often"]["continue"], callback_data="view_cat!" + str(None) + "!main_cat")
            builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_add_product")
            builder.adjust(1)

            await query.message.edit_reply_markup(reply_markup=builder.as_markup())
        else: 
            text = languages[lang_code]["answers"]["manage_product_router"]["not_correct"]["add_product_1"] + str(limits['max_own_product_count'])
            text += languages[lang_code]["answers"]["manage_product_router"]["not_correct"]["add_product_2"]
            await query.message.edit_text(text)

            builder = InlineKeyboardBuilder()
            builder.button(text=languages[lang_code]["keyboards"]["user_router"]["user_main_menu"]["tariffs"],  callback_data="tariffs")
            builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="view_my_catalog!" + str(catalog_id))
            builder.adjust(1)

            await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    else:
        if user_info["blocking"] == "blocked":
            text = languages[lang_code]["answers"]["blocked"]
            await query.message.edit_text(text)
            await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!" + str(catalog_id), lang_code))
        elif user_info["blocking"] == "waiting_attach":
            text = languages[lang_code]["answers"]["blocked_w_a"]
            await query.message.edit_text(text)
            await query.message.edit_reply_markup(reply_markup=back_kb("my_catalogs"))
        
    await conn.close()


@manage_product_router.message(EditProductForm.edit_product_name, F.text)
@manage_product_router.message(AddProductForm.add_product_name, F.text)
async def add_product_name(message: Message, state: FSMContext, lang_code: str):
    product_name = html.quote(message.text)
    if len(product_name) > 2 and len(product_name) < 50:
        conn = await asyncpg.connect(**connection_params)
        cbck_mess = None
        if await state.get_state() == AddProductForm.add_product_name.state:
            await state.update_data({"name": product_name})
            await state.set_state(AddProductForm.add_product_desc)
            cbck_mess = await message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["add_product"]["write_desc"], reply_markup=cancel_inline_kb("cancel_add_product", lang_code))
        else: 
            
            data = await state.get_data()

            product_id = data["product_id"]
            await conn.execute("UPDATE products SET name = $1 WHERE id = $2", product_name, product_id)

            catalog_id = await conn.fetchval("SELECT catalog_id FROM products WHERE id = $1", product_id)
            await rm_catalog_from_publication(catalog_id, conn)

            cbck_mess = await message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["edit_product"]["name_edited"], reply_markup=back_kb("edit_product!"+str(product_id), lang_code))
            await state.clear()

        await add_to_waiting_cbck_buffer(conn, cbck_mess)
        await conn.close()
    else: 
        await message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["not_correct"]["product_name"])

@manage_product_router.message(EditProductForm.edit_product_desc, F.text)
@manage_product_router.message(AddProductForm.add_product_desc, F.text)
async def add_product_desc(message: Message, state: FSMContext, lang_code: str):
    product_desc = html.quote(message.text)
    if len(product_desc) > 10:
        conn = await asyncpg.connect(**connection_params)
        cbck_mess = None
        if await state.get_state() == AddProductForm.add_product_desc.state:
            await state.update_data({"desc": product_desc})
            await state.set_state(AddProductForm.add_product_photo)

            builder = InlineKeyboardBuilder()
            builder.button(text=languages[lang_code]["keyboards"]["products"]["finish_adding_photos"], callback_data="finish_adding_photos")
            builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_add_product")
            builder.adjust(1)

            cbck_mess = await message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["add_product"]["send_photo"], reply_markup=builder.as_markup())
        else:
            data = await state.get_data()

            product_id = data["product_id"]
            await update_product_desc(product_id, product_desc, conn)

            catalog_id = await conn.fetchval("SELECT catalog_id FROM products WHERE id = $1", product_id)
            await rm_catalog_from_publication(catalog_id, conn)

            cbck_mess = await message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["edit_product"]["desc_edited"], reply_markup=back_kb("edit_product!"+str(product_id), lang_code))
            await state.clear()

        await add_to_waiting_cbck_buffer(conn, cbck_mess)
        await conn.close()
    else: 
        await message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["not_correct"]["product_desc"])

@manage_product_router.message(EditProductForm.edit_add_product_photo, F.photo)
@manage_product_router.message(AddProductForm.add_product_photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext, lang_code: str):
    data = await state.get_data()

    conn = await asyncpg.connect(**connection_params)

    photo = None
    #print(message.photo)
    MAX_PHOTO_SIZE = await conn.fetchval("SELECT MAX_PHOTO_SIZE FROM config LIMIT 1")
    for photo_size in reversed(message.photo):
        if photo_size.file_size < MAX_PHOTO_SIZE:
            photo = photo_size
            break
    
    #print(photo)

    cbck_mess = None
    state_now = await state.get_state()

    if photo != None:
        if "photos" in data:
            photos = data["photos"]
            photos: list

            photos.append(photo)
            
            await state.update_data({"photos": photos})
        else:
            await state.update_data({"photos": [photo]})

        builder = InlineKeyboardBuilder()
        builder.button(text=languages[lang_code]["keyboards"]["products"]["finish_adding_photos"], callback_data="finish_adding_photos")

        if state_now == AddProductForm.add_product_photo:
            builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_add_product")
            builder.adjust(1)
            cbck_mess = await message.answer(languages[lang_code]["answers"]["manage_product_router"]["add_product"]["send_next_photo"], reply_markup=builder.as_markup())
        else:
            product_id = data["product_id"]
            builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_edit_product!" + str(product_id))
            builder.adjust(1)
            cbck_mess = await message.answer(languages[lang_code]["answers"]["manage_product_router"]["add_product"]["send_next_photo"], reply_markup=builder.as_markup())
    else:
        if state_now == AddProductForm.add_product_photo:
            cbck_mess = await message.answer(languages[lang_code]["answers"]["errors"]["smth_t_s_f"], reply_markup=cancel_inline_kb("cancel_add_product", lang_code))
        else:
            product_id = data["product_id"]
            cbck_mess = await message.answer(languages[lang_code]["answers"]["errors"]["smth_t_s_f"], reply_markup=cancel_inline_kb("cancel_edit_product!" + str(product_id), lang_code))
    

    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await conn.close()

@manage_product_router.callback_query(EditProductForm.edit_add_product_photo, F.data == "finish_adding_photos")
async def add_product_finish(query: CallbackQuery, state: FSMContext, bot: Bot, lang_code: str):
    data = await state.get_data()
    conn = await asyncpg.connect(**connection_params)

    product_id = data["product_id"]

    ####
    if "photos" in data:
        photos = data["photos"]

        photo_num = 0
        for photo in photos:
            await add_product_media_file(photo, product_id, photo_num, bot)
            photo_num += 1
    ####
    ####
    # dir_path = old_make_product_media_dir(str(product_id))
    # if "photos" in data:
    #     photos = data["photos"]

    #     photo_num = 0
    #     for photo in photos:
    #         await old_add_product_media_file(photo, dir_path, photo_num, bot)
    #         photo_num += 1
    ####

        catalog_id = await conn.fetchval("SELECT catalog_id FROM products WHERE id = $1", product_id)
        await rm_catalog_from_publication(catalog_id, conn)

    await query.message.edit_text(text=languages[lang_code]["answers"]["manage_product_router"]["edit_product"]["photo_added"])
    await query.message.edit_reply_markup(reply_markup=back_kb("edit_product!"+str(product_id), lang_code))
    await state.clear()

    await conn.close()
    

@manage_product_router.callback_query(AddProductForm.add_product_photo, F.data == "finish_adding_photos")
async def add_product_finish(query: CallbackQuery, state: FSMContext, bot: Bot, lang_code: str):
    data = await state.get_data()
    conn = await asyncpg.connect(**connection_params)

    await rm_catalog_from_publication(data["catalog_id"], conn)
    await conn.execute("DELETE FROM moderation_list WHERE catalog_id = $1", data["catalog_id"])

    product_id = await insert_into_products(data["catalog_id"], data["cat_id"], data["name"], data["desc"], conn)
    
    ####
    if "photos" in data:
        photos = data["photos"]

        photo_num = 0
        for photo in photos:
            await add_product_media_file(photo, product_id, photo_num, bot)
            photo_num += 1
    ####            
    ####
    # dir_path = old_make_product_media_dir(str(product_id))
    # if "photos" in data:
    #     photos = data["photos"]

    #     photo_num = 0
    #     for photo in photos:
    #         await old_add_product_media_file(photo, dir_path, photo_num, bot)
    #         photo_num += 1
    ####

    #await message.answer(text="...", reply_markup=types.ReplyKeyboardRemove())
    await query.message.edit_text(text=languages[lang_code]["answers"]["manage_product_router"]["add_product"]["product_added"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!" + str(data["catalog_id"]), lang_code))
    
    await state.clear()
    await conn.close()




@manage_product_router.callback_query(CallbackArgFilter("delete_product"))
async def delete_product(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    product_id = int(query.data.split("!")[1])
    catalog_id = int(query.data.split("!")[2])

    ####
    remove_product_media_dir(str(product_id))
    ####
    ####
    # old_remove_product_media_dir(str(product_id))
    ####
    await conn.execute("DELETE FROM products WHERE id = $1", product_id)
    catalog_info = await conn.fetchrow("SELECT * FROM catalogs WHERE id = $1", catalog_id)
    if catalog_info["status"] == "rejected":
        await conn.execute("UPDATE catalogs SET status = $1", "not_published")

    await query.message.edit_text(languages[lang_code]["answers"]["manage_product_router"]["product_deleted"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_my_catalog!"+str(catalog_id), lang_code))

    await conn.close()


@manage_product_router.callback_query(CallbackArgFilter("edit_product"))
async def edit_product(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    product_id = int(query.data.split("!")[1])

    product_info = await conn.fetchrow("SELECT name, description, catalog_id, category_id FROM products WHERE id = $1", product_id)
    cat_name = await conn.fetchval("SELECT name FROM categories WHERE id = $1", product_info["category_id"])

    #photos_paths = await conn.fetch("SELECT file_path FROM photos WHERE product_id = $1", product_id)

    cbck_messages = []

    cbck_messages.append(await query.message.answer(languages[lang_code]["texts"]["product_text"]["name"] + product_info["name"], 
                                              reply_markup=edit_kb("edit_product_name!" + str(product_id), lang_code)))
    cbck_messages.append(await query.message.answer(languages[lang_code]["texts"]["product_text"]["cat"] + languages[lang_code]["words"]["categories"][cat_name], 
                                              reply_markup=edit_kb("edit_product_cat!" + str(product_id), lang_code)))
    cbck_messages.append(await query.message.answer(languages[lang_code]["texts"]["product_text"]["desc"] + product_info["description"],
                                              reply_markup=edit_kb("edit_product_desc!" + str(product_id), lang_code)))

    ####
    for photo_obj in get_product_objects(product_id):
        photo = photo_obj.get()
        cbck_messages.append(await query.message.answer_photo(photo=BufferedInputFile(file=photo["Body"].read(), filename=str(product_id)), 
                                                        reply_markup=del_kb("del_product_photo!"+ str(product_id) + "!" + photo_obj.key, lang_code)))
    ####
    ####
    # dir_path = old_get_products_dir_path() + str(product_id)
    # for photo_file_name in get_product_objects(product_id):
    #     cbck_messages.append(await query.message.answer_photo(photo=FSInputFile(dir_path + "/" + photo_file_name), 
    #                                                     reply_markup=del_kb("del_product_photo!"+ str(product_id) + "!" + photo_file_name, lang_code)))
    ####
        
      
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["manage_product_router"]["edit_product_menu"]["add_photo"], 
                   callback_data="add_product_photo!" + str(product_id))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], 
                   callback_data="view_my_product!"+ str(product_id))
    builder.adjust(1)
        
    cbck_messages.append(await query.message.answer(text=languages[lang_code]["answers"]["menus"]["menu"], reply_markup=builder.as_markup()))

    for mess in cbck_messages:
        await add_to_waiting_cbck_buffer(conn, mess)

    await delete_cbck_message(conn, query.message)

    await conn.close()

@manage_product_router.callback_query(CallbackArgFilter("edit_product_name"))
async def edit_product_name(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    product_id = int(query.data.split("!")[1])

    await state.update_data({"product_id": product_id})
    await state.set_state(EditProductForm.edit_product_name)
    cbck_message = await query.message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["add_product"]["write_name"], reply_markup=cancel_inline_kb("cancel_edit_product!"+str(product_id), lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@manage_product_router.callback_query(CallbackArgFilter("edit_product_desc"))
async def edit_product_desc(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    product_id = int(query.data.split("!")[1])

    await state.update_data({"product_id": product_id})
    await state.set_state(EditProductForm.edit_product_desc)
    cbck_message = await query.message.answer(text=languages[lang_code]["answers"]["manage_product_router"]["add_product"]["write_desc"], reply_markup=cancel_inline_kb("cancel_edit_product!"+str(product_id), lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)

    await conn.close()


@manage_product_router.callback_query(CallbackArgFilter("edit_product_cat"))
async def edit_product_cat(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    product_id = int(query.data.split("!")[1])

    await state.update_data({"product_id": product_id})
    await state.set_state(EditProductForm.edit_product_cat)

    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["continue"], callback_data="view_cat!" + str(None) + "!main_cat")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_edit_product!" + str(product_id))
    builder.adjust(1)

    await query.message.edit_text(languages[lang_code]["answers"]["menus"]["menu"])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()

@manage_product_router.callback_query(CallbackArgFilter("add_product_photo"))
async def add_product_photo(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    product_id = int(query.data.split("!")[1])

    await state.update_data({"product_id": product_id})
    await state.set_state(EditProductForm.edit_add_product_photo)

    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["products"]["finish_adding_photos"], callback_data="finish_adding_photos")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_edit_product!" + str(product_id))
    builder.adjust(1)

    cbck_message = await query.message.answer(languages[lang_code]["answers"]["manage_product_router"]["add_product"]["send_photo"], reply_markup=builder.as_markup())
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@manage_product_router.callback_query(CallbackArgFilter("del_product_photo"))
async def edit_product_name(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    product_id = int(query.data.split("!")[1])

    ####
    obj_key = query.data.split("!")[2]
    delete_obj(obj_key)
    ####
    ####
    # photo_file_name = query.data.split("!")[2]
    # delete_product_photo(product_id, photo_file_name)
    ####
    
    cbck_mess = await query.message.answer(languages[lang_code]["answers"]["manage_product_router"]["edit_product"]["photo_deleted"], reply_markup=back_kb("edit_product!"+ str(product_id), lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()
