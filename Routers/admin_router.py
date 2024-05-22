from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb, cancel_inline_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.tariff_kbs import tariffs_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu, admin_main_menu_kb
from Utils.Keyboards.catalogs_products_kbs import my_catalogs_menu_kb, my_product_menu_kb
from States.auth_states import InvitedRegForm
from States.admin_states import AttachAccForm, FilterWithdrawalsForm, FilterModerationsForm, DbQueryForm, CustomNotifyForm
from Filters.filters import CallbackArgFilter, RoleFilter, StatesFilter
from aiogram.utils.media_group import MediaGroupBuilder
from Utils.Methods.complect_ref_stat import complect_ref_stat, complecting

from Utils.Methods.mailing import permanent_mailing_task
from Utils.Methods.tariff_upd import permanent_tariff_update_task, add_to_tariff_buffer, activate_in_tariff_buffer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Sources.files import languages
from Files import buffer
import random
from Utils.Methods.moderation import reset_moderator

from Sources.files import set_last_tariff_check_date

import os

from datetime import datetime, timedelta

import pytz




admin_router = Router()

admin_router.message.filter(RoleFilter("admin"))
admin_router.callback_query.filter(RoleFilter("admin"))


# @admin_router.message(Command("cancel"), StatesFilter(AttachAccForm.__all_states_names__))
# async def cancel_attaching_acc(message: Message, state: FSMContext, lang_code: str):
#     conn = await asyncpg.connect(**connection_params)

#     text = languages[lang_code]["answers"]["admin_router"]["cancel"]["attaching_acc"]
#     cbck_message = await message.answer(text=text, reply_markup=back_kb("service_acc_manager", lang_code))
#     await add_to_waiting_cbck_buffer(conn, cbck_message)

#     await state.clear()
#     await conn.close()

@admin_router.callback_query(F.data == "cancel_attach_acc")
async def cancel_attach_acc(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    text = languages[lang_code]["answers"]["admin_router"]["cancel"]["attaching_acc"]
    cbck_message = await query.message.answer(text=text, reply_markup=back_kb("service_acc_manager", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)

    await state.clear()
    await conn.close()


@admin_router.callback_query(F.data == "restart_permanent_tasks")
async def test_start_mailing(query: CallbackQuery, bot: Bot, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    config_row = await conn.fetchrow("SELECT PERMANENT_MAILING_TASK_INTERVAL_MINS, PERMANENT_TARIFF_UPDATE_TASK_MINS FROM config LIMIT 1")

    #print(config_row)
    # if buffer.permanent_mailing_job != None:
    #     print(buffer.permanent_mailing_job.id)
    #     buffer.permanent_mailing_job = buffer.scheduler.remove_job(buffer.permanent_mailing_job.id)
    # if buffer.permanent_tariff_update_job != None:
    #     buffer.permanent_tariff_update_job = buffer.scheduler.remove_job(buffer.permanent_tariff_update_job.id)
    
    #print(buffer.scheduler.get_jobs())

    buffer.scheduler.remove_all_jobs()

    buffer.scheduler.add_job(permanent_mailing_task, "interval", minutes=config_row["permanent_mailing_task_interval_mins"], kwargs={"bot": bot})
    buffer.scheduler.add_job(permanent_tariff_update_task, "interval", minutes=config_row["permanent_tariff_update_task_mins"])

    if not buffer.scheduler.running:
        buffer.scheduler.start()

    set_last_tariff_check_date(datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))))

    await query.message.edit_text(languages[lang_code]["answers"]["admin_router"]["restart_tasks"])
    await query.message.edit_reply_markup(reply_markup=back_kb("technical_menu", lang_code))

    await conn.close()



@admin_router.callback_query(F.data == "main_menu")
async def main_menu(query:CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    cbck_message = await query.message.answer(languages[lang_code]["answers"]["menus"]["menu"], reply_markup=admin_main_menu_kb(lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await delete_cbck_message(conn, query.message)
    await conn.close()

@admin_router.message(Command("menu"))
async def main_menu_cbck(message: Message, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    #print(message.from_user.username)
    cbck_message = await message.answer(languages[lang_code]["answers"]["menus"]["menu"], reply_markup=admin_main_menu_kb(lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_message)
    await conn.close()


@admin_router.callback_query(F.data == "cancel_operation")
async def cancel_withdrawal_list(query: CallbackQuery, state: FSMContext, lang_code):
    conn = await asyncpg.connect(**connection_params)

    await state.clear()
    await query.message.edit_text(languages[lang_code]["answers"]["cancel_operation"])
    await query.message.edit_reply_markup(reply_markup=back_kb("main_menu", lang_code))

    await conn.close()

@admin_router.callback_query(F.data == "cancel_s_l_operation")
async def cancel_withdrawal_list(query: CallbackQuery, state: FSMContext, lang_code):
    conn = await asyncpg.connect(**connection_params)

    await state.clear()
    await query.message.edit_text(languages[lang_code]["answers"]["cancel_operation"])
    await query.message.edit_reply_markup(reply_markup=back_kb("stat_lists_menu", lang_code))

    await conn.close()


@admin_router.callback_query(F.data == "withdrawal_list")
async def withdrawal_list_start(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    await state.set_state(FilterWithdrawalsForm.withdrawals_filter)

    cbck_mess = await query.message.answer(text=html.quote(languages[lang_code]["answers"]["admin_router"]["write_withdrawal_filter"]), reply_markup=cancel_inline_kb("cancel_s_l_operation", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@admin_router.message(F.text, FilterWithdrawalsForm.withdrawals_filter)
async def withdrawals_filter_and_results(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    filters = message.text.split(",")
    db_query = "SELECT * FROM withdrawal_list "
    params = []
    order_by = "ORDER BY moderation_date DESC"

    param_num = 0
    for index, filter in enumerate(filters):
        if filter != "*":
            param_num += 1
            if len(params) > 0:
                db_query += "AND "
            else:
                db_query += "WHERE "

            if index == 0:
                db_query += f"id = ${param_num} "
            elif index == 1:
                db_query += f"user_id = ${param_num} "
            elif index == 2:
                db_query += f"moderator_id = ${param_num} "
            
            if index == 3:
                if filter == "None":
                    db_query += f"status IS NULL "
                else:
                    db_query += f"status = ${param_num} "
                    params.append(filter)
            else:
                params.append(int(filter))
    
    db_query += order_by
    #print(db_query)

    results = await conn.fetch(db_query, *params)

    file_text = "id | user_id | moderator_id | bank_card_number | amount | moderation_date | status\n\n"
    for withdrawal in results:
        file_text += f"{withdrawal['id']} | {withdrawal['user_id']} | {withdrawal['moderator_id']} | {withdrawal['bank_card_number']} | {withdrawal['amount']} | {withdrawal['moderation_date']} | {withdrawal['status']}\n"

    cbck_mess = await message.answer_document(document=BufferedInputFile(file_text.encode(), "withdrawal_list.txt"), reply_markup=back_kb("stat_lists_menu", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_mess)

    await state.clear()
    await conn.close()

#------

@admin_router.callback_query(F.data == "moderation_list")
async def withdrawal_list_start(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    await state.set_state(FilterModerationsForm.moderations_filter)

    cbck_mess = await query.message.answer(text=html.quote(languages[lang_code]["answers"]["admin_router"]["write_moderation_filter"]), reply_markup=cancel_inline_kb("cancel_s_l_operation", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@admin_router.message(F.text, FilterModerationsForm.moderations_filter)
async def withdrawals_filter_and_results(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    filters = message.text.split(",")
    db_query = "SELECT * FROM moderation_list "
    params = []
    order_by = "ORDER BY moderation_date DESC"

    param_num = 0
    for index, filter in enumerate(filters):
        if filter != "*":
            param_num += 1
            if len(params) > 0:
                db_query += "AND "
            else:
                db_query += "WHERE "

            if index == 0:
                db_query += f"catalog_id = ${param_num} "
            elif index == 1:
                db_query += f"moderator_id = ${param_num} "
            
            if index == 2:
                if filter == "None":
                    db_query += f"status IS NULL "
                else:
                    db_query += f"status = ${param_num} "
                    params.append(filter)
            else:
                params.append(int(filter))
            
    
    db_query += order_by
    #print(db_query)

    results = await conn.fetch(db_query, *params)

    file_text = "id | catalog_id | moderator_id | moderation_date | status\n\n"
    for withdrawal in results:
        file_text += f"{withdrawal['id']} | {withdrawal['catalog_id']} | {withdrawal['moderator_id']} | {withdrawal['moderation_date']} | {withdrawal['status']}\n"

    cbck_mess = await message.answer_document(document=BufferedInputFile(file_text.encode(), "moderation_list.txt"), reply_markup=back_kb("stat_lists_menu", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_mess)

    await state.clear()
    await conn.close()


@admin_router.callback_query(F.data == "technical_menu")
async def technical_menu(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["technical_menu"]["restart_per_tasks"], callback_data="restart_permanent_tasks")
    if buffer.bot_blocked == False:
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["technical_menu"]["bot_block_alert"], callback_data="bot_block_alert")
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["technical_menu"]["bot_started_notify"], callback_data="bot_started_notify")
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["technical_menu"]["custom_notify"], callback_data="custom_notify")
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["technical_menu"]["block_bot"], callback_data="block_bot")
    else:
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["technical_menu"]["unblock_bot"], callback_data="unblock_bot")
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["technical_menu"]["db_query"], callback_data="db_query")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)

    cbck_mess = await query.message.answer(languages[lang_code]["answers"]["menus"]["tech_menu"], reply_markup=builder.as_markup())

    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@admin_router.callback_query(F.data == "stat_lists_menu")
async def technical_menu(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["view_ref_s"], callback_data="view_ref_stat")
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["stat_lists_menu"]["withdrawal_list"], callback_data="withdrawal_list")
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["stat_lists_menu"]["moderation_list"], callback_data="moderation_list")
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["stat_lists_menu"]["traffic_sources"], callback_data="traffic_sources")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)

    cbck_mess = await query.message.answer(languages[lang_code]["answers"]["menus"]["s_l_menu"], reply_markup=builder.as_markup())
    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@admin_router.callback_query(F.data == "db_query")
async def start_db_query(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    
    await state.set_state(DbQueryForm.db_query)

    cbck_mess = await query.message.answer(text=languages[lang_code]["answers"]["admin_router"]["write_db_query"], reply_markup=cancel_inline_kb("cancel_operation", lang_code))

    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@admin_router.message(DbQueryForm.db_query, F.text)
async def db_query(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    try:
        answer = await conn.fetch(message.text)
    except Exception as e:
        answer = str(e) + str(e.__traceback__)
        print(e)
        print(e.__traceback__)

    #print(answer)

    file_text = str(answer)

    #print(file_text)

    cbck_mess = None

    if answer == []:
        cbck_mess = await message.answer(text="Success", reply_markup=back_kb("technical_menu", lang_code))
    else:
        cbck_mess = await message.answer_document(document=BufferedInputFile(file_text.encode(), "db_query_answer.txt"), reply_markup=back_kb("technical_menu", lang_code))

    await add_to_waiting_cbck_buffer(conn, cbck_mess)

    await state.clear()
    await conn.close()

@admin_router.callback_query(F.data == "bot_block_alert")
async def bot_block_alert(query: CallbackQuery, bot: Bot, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    receivers = await conn.fetch("SELECT tg_user_id, language_code FROM accounts WHERE tg_user_id IS NOT NULL")
    for receiver in receivers:
        text = languages[receiver["language_code"]]["texts"]["notifications"]["bot_block_alert"]
        try:
            await bot.send_message(chat_id=receiver["tg_user_id"], text=text)
        except Exception as e:
            print(e)
            print(e.__traceback__)
    await query.answer()

    await conn.close()

@admin_router.callback_query(F.data == "bot_started_notify")
async def bot_block_alert(query: CallbackQuery, bot: Bot, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    receivers = await conn.fetch("SELECT tg_user_id, language_code FROM accounts WHERE tg_user_id IS NOT NULL")
    for receiver in receivers:
        text = languages[receiver["language_code"]]["texts"]["notifications"]["bot_started"]
        try:
            await bot.send_message(chat_id=receiver["tg_user_id"], text=text)
        except Exception as e:
            print(e)
            print(e.__traceback__)
    await query.answer()

    await conn.close()

@admin_router.callback_query(F.data == "custom_notify")
async def start_db_query(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    
    await state.set_state(CustomNotifyForm.custom_message)

    cbck_mess = await query.message.answer(text=languages[lang_code]["answers"]["admin_router"]["send_custom_message"], reply_markup=cancel_inline_kb("cancel_operation", lang_code))

    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@admin_router.message(CustomNotifyForm.custom_message)
async def bot_block_alert(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    receivers = await conn.fetch("SELECT tg_user_id, language_code FROM accounts WHERE tg_user_id IS NOT NULL")
    for receiver in receivers:
        try:
            await message.send_copy(chat_id=receiver["tg_user_id"])
        except Exception as e:
            print(e)
            print(e.__traceback__)

    await state.clear()
    await conn.close()

@admin_router.callback_query(F.data == "block_bot")
async def block_bot(query: CallbackQuery, bot: Bot, lang_code):
    conn = await asyncpg.connect(**connection_params)

    buffer.bot_blocked = True

    if buffer.scheduler.running:
        buffer.scheduler.shutdown()

    receivers = await conn.fetch("SELECT tg_user_id, language_code FROM accounts WHERE tg_user_id IS NOT NULL")
    for receiver in receivers:
        text = languages[receiver["language_code"]]["texts"]["notifications"]["bot_blocked"]
        try:
            await bot.send_message(chat_id=receiver["tg_user_id"], text=text)
        except Exception as e:
            print(e)
            print(e.__traceback__)
        
    await delete_cbck_message(conn, query.message)
    await query.answer()

    await conn.close()

@admin_router.callback_query(F.data == "unblock_bot")
async def block_bot(query: CallbackQuery, bot: Bot, lang_code):
    conn = await asyncpg.connect(**connection_params)

    buffer.bot_blocked = False

    receivers = await conn.fetch("SELECT tg_user_id, language_code FROM accounts WHERE tg_user_id IS NOT NULL")
    for receiver in receivers:
        text = languages[receiver["language_code"]]["texts"]["notifications"]["bot_unblocked"]
        try:
            await bot.send_message(chat_id=receiver["tg_user_id"], text=text)
        except Exception as e:
            print(e)
            print(e.__traceback__)

    await delete_cbck_message(conn, query.message)
    await query.answer()

    await conn.close()

@admin_router.callback_query(F.data == "traffic_sources")
async def view_source_traffic(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    text = html.quote(languages[lang_code]["texts"]["resources_text"]["output_format_res"]) + "\n"

    stat = await conn.fetch("SELECT source, COUNT(*) as amount FROM accounts WHERE role = 'user' GROUP BY source")

    blocked_stat = await conn.fetch("SELECT blocking, COUNT(*) as amount FROM accounts GROUP BY blocking")

    #print(stat)

    for source in stat:
        text += f"{source['source']} : {source['amount']} \n" 

    text += html.quote(languages[lang_code]["texts"]["resources_text"]["output_format_block"]) + "\n"

    for blocking in blocked_stat: 
        text += f"{blocking['blocking']} : {blocking['amount']} \n" 

    await query.message.edit_text(text=text)
    await query.message.edit_reply_markup(reply_markup=back_kb("stat_lists_menu", lang_code))

    await conn.close()


@admin_router.callback_query(F.data == "view_ref_stat")
async def view_ref_link(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    next_line = await conn.fetch("SELECT * FROM accounts WHERE referer_id IS NULL AND role = 'user'")
    ref_stat = await complecting(next_line, conn, [], 0)

    line_number = 1
    line_text = ""
    for line_count in ref_stat["lines_list"]:
            line_text += languages[lang_code]["texts"]["ref_stat_text"]["line"] + f" {line_number} : {line_count} \n"
            line_number += 1

    text = line_text
    text += languages[lang_code]["texts"]["ref_stat_text"]["amount"] + f" {ref_stat['full_count']}"
    await query.message.edit_text(text=text)
    await query.message.edit_reply_markup(reply_markup=back_kb("stat_lists_menu", lang_code))

    await conn.close()


@admin_router.callback_query(F.data == "service_acc_manager")
async def service_acc_manager_func(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["service_acc_manager"]["free_h_a_m"], callback_data="head_acc_manager")
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["service_acc_manager"]["support_a_m"], callback_data="support_acc_manager")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)

    await query.message.edit_text(languages[lang_code]["answers"]["admin_router"]["service_a_m"])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()


@admin_router.callback_query(F.data == "head_acc_manager")
async def head_acc_manager(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    head_accs = await conn.fetch("SELECT * FROM accounts WHERE role = 'user' and referer_id IS NULL")
    

    builder = InlineKeyboardBuilder()
    for free_acc in head_accs:
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["head_acc_manager"]["f_h_a"] + " " + str(free_acc["id"]), callback_data="view_head_acc!"+ str(free_acc["id"]))

    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["head_acc_manager"]["add_new_h_a"], callback_data="add_head_acc")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="service_acc_manager")
    builder.adjust(1)

    await query.message.edit_text(languages[lang_code]["answers"]["admin_router"]["free_h_a_m"])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    
    await conn.close()



@admin_router.callback_query(F.data == "support_acc_manager")
async def support_acc_manager(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    support_accs = await conn.fetch("SELECT * FROM accounts WHERE role = 'support'")

    builder = InlineKeyboardBuilder()
    for support_acc in support_accs:
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["support_acc_manager"]["s_a"] + " " + str(support_acc["id"]), callback_data="view_support_acc!"+ str(support_acc["id"]))

    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["support_acc_manager"]["add_new_s_a"], callback_data="add_support_acc")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="service_acc_manager")
    builder.adjust(1)

    await query.message.edit_text(languages[lang_code]["answers"]["admin_router"]["support_a_m"])
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    
    await conn.close()

#---------------

@admin_router.callback_query(F.data == "add_head_acc")
async def add_head_acc(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    ref_link_hasher = str(datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS")))) + str(random.randint(-1000000,1000000))
    ref_link = hashlib.sha256(ref_link_hasher.encode()).hexdigest()
    ref_link = ref_link[0:50]


    acc_id = await conn.fetchval("INSERT INTO accounts (ref_link, role, bonuses) VALUES ($1, 'user', 0) RETURNING id", ref_link)

    await add_to_tariff_buffer(acc_id, None, conn)
    #await add_to_tariff_buffer(acc_id, timedelta(days=30), conn, "advanced")

    await activate_in_tariff_buffer(acc_id, conn)

    await conn.execute("INSERT INTO logs (description, date) VALUES ($1, $2)", f"Free head account added. acc_id = {str(acc_id)}", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))))

    await query.message.edit_text(languages[lang_code]["answers"]["admin_router"]["f_h_a_created"])
    await query.message.edit_reply_markup(reply_markup=back_kb("head_acc_manager", lang_code))

    await conn.close()
    
#-----
        
@admin_router.callback_query(F.data == "add_support_acc")
async def add_head_acc(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    acc_id = await conn.fetchval("INSERT INTO accounts (role) VALUES ('support') RETURNING id")

    await conn.execute("INSERT INTO logs (description, date) VALUES ($1, $2)", f"Support account added. acc_id = {str(acc_id)}", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))))

    await query.message.edit_text(languages[lang_code]["answers"]["admin_router"]["s_a_created"])
    await query.message.edit_reply_markup(reply_markup=back_kb("support_acc_manager", lang_code))

    await conn.close()
    
#-------------------------


@admin_router.callback_query(CallbackArgFilter("view_head_acc"))
async def view_free_acc(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    acc_id = int(query.data.split("!")[1])

    user_info = await conn.fetchrow("SELECT ref_link, bonuses, login FROM accounts WHERE id = $1", acc_id)
    
    ref_stat = await complect_ref_stat(acc_id, conn)
    line_number = 1
    line_text = ""
    for line_count in ref_stat["lines_list"]:
        line_text += languages[lang_code]["texts"]["ref_stat_text"]["line"] + str(line_number) + ": " + str(line_count) + "\n"
        line_number += 1

    builder = InlineKeyboardBuilder()
    if user_info["login"] == None:
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["attach_acc"], callback_data="attach_acc!" + str(acc_id))
        builder.button(text=languages[lang_code]["keyboards"]["often"]["del"], callback_data="delete_service_acc!" + str(acc_id))
    else:
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["detach_acc"], callback_data="detach_head_acc!" + str(acc_id))

    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="head_acc_manager")
    builder.adjust(1)

    #text=languages[lang_code]["texts"]["acc_text"]["login"] + " " + user_info["login"] + "\n"
    text = ""
    if user_info["login"] != None:
        text += languages[lang_code]["texts"]["acc_text"]["login"] + user_info["login"] + "\n\n"
    else:
        text += languages[lang_code]["texts"]["ref_link"] + f" { os.getenv('BOT_LINK') }?start=ref{ user_info['ref_link'] } \n\n"

    text += line_text 
    text += languages[lang_code]["texts"]["ref_stat_text"]["amount"] + " " + str(ref_stat["full_count"]) + "\n\n"

    text += languages[lang_code]["texts"]["acc_text"]["id"] + str(acc_id) + "\n"
    text += languages[lang_code]["texts"]["acc_text"]["bonuses"] + " " + str(user_info["bonuses"]) + "\n"
    text += languages[lang_code]["texts"]["acc_text"]["f_h_a_menu"]
    await query.message.edit_text(text=text)
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()  

#------------
    
@admin_router.callback_query(CallbackArgFilter("view_support_acc"))
async def view_sup_acc(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    acc_id = int(query.data.split("!")[1])

    user_info = await conn.fetchrow("SELECT login, tg_user_id FROM accounts WHERE id = $1", acc_id)
    
    builder = InlineKeyboardBuilder()
    if user_info["login"] == None:
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["attach_acc"], callback_data="attach_acc!" + str(acc_id))
        builder.button(text=languages[lang_code]["keyboards"]["often"]["del"], callback_data="delete_service_acc!" + str(acc_id))
    else: 
        builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["detach_acc"], callback_data="detach_support_acc!" + str(acc_id))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="support_acc_manager")
    builder.adjust(1)

    text = languages[lang_code]["texts"]["acc_text"]["id"] + str(acc_id) + "\n"
    # if user_info["tg_user_id"] != None:
    #     text += languages[lang_code]["texts"]["acc_text"]["telegram_id"] + str(user_info["tg_user_id"]) + "\n"
    if user_info["login"] != None:
        text += languages[lang_code]["texts"]["acc_text"]["login"] + user_info["login"] + "\n"
    text += languages[lang_code]["texts"]["acc_text"]["s_a_menu"]

    await query.message.edit_text(text)
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

    await conn.close()  


@admin_router.callback_query(CallbackArgFilter("delete_service_acc"))
async def view_sup_acc(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    acc_id = int(query.data.split("!")[1])

    #user_info = await conn.fetchrow("SELECT login, tg_user_id FROM accounts WHERE id = $1", acc_id)
    
    await reset_moderator(acc_id, conn)

    await conn.execute("DELETE FROM accounts WHERE id = $1", acc_id)

    await service_acc_manager_func(query, lang_code)

    await conn.close()

#----
    
@admin_router.callback_query(CallbackArgFilter("attach_acc"))
async def attach_acc(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    acc_id = int(query.data.split("!")[1])

    await state.set_state(AttachAccForm.attaching_acc_id)
    await state.update_data({"acc_id": acc_id})

    cbck_mess = await query.message.answer(languages[lang_code]["answers"]["admin_router"]["attach_acc"], reply_markup=cancel_inline_kb("cancel_attach_acc", lang_code))
    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close() 

@admin_router.message(AttachAccForm.attaching_acc_id, F.text)
async def attaching_acc(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    data = await state.get_data()

    attaching_id = int(html.quote(message.text))
    attaching_acc = await conn.fetchrow("SELECT * FROM accounts WHERE id = $1", attaching_id)

    acc_id = data["acc_id"]

    cbck_message =  None

    if attaching_acc["blocking"] == "waiting_attach" and await conn.fetchval("SELECT COUNT(*) FROM accounts WHERE referer_id = $1", attaching_acc["id"]) == 0 and await conn.fetchval("SELECT COUNT(*) FROM catalogs WHERE owner_id = $1", attaching_acc["id"]) == 0:
        await conn.execute("UPDATE accounts SET tg_user_id = $1, login = $2, language_code = $3, blocking = NULL, show_award_notifications = $4 WHERE id = $5", 
                        attaching_acc["tg_user_id"], attaching_acc["login"], attaching_acc["language_code"], attaching_acc["show_award_notifications"], acc_id)
        
        await conn.execute("DELETE FROM tariff_buffer WHERE user_id = $1", attaching_acc["id"])
        await conn.execute("DELETE FROM accounts WHERE id = $1", attaching_acc["id"])

        acc_info = await conn.fetchrow("SELECT role FROM accounts WHERE id = $1", acc_id)
        if acc_info["role"] == "user":
            if await add_to_tariff_buffer(acc_id, timedelta(days=365), conn, "vip") == False:
                await conn.execute("UPDATE tariff_buffer SET remains = $1 WHERE user_id = $2", timedelta(days=365), acc_id)
            await activate_in_tariff_buffer(acc_id, conn, "vip")
        #await conn.execute("UPDATE accounts SET tg_user_id = NULL, login = NULL WHERE id = $1", attaching_acc["id"])
        
        cbck_message = await message.answer(languages[lang_code]["answers"]["admin_router"]["acc_attached"], reply_markup=back_kb("service_acc_manager", lang_code))
    else:
        cbck_message = await message.answer(languages[lang_code]["answers"]["admin_router"]["not_correct"]["attach_acc"], reply_markup=back_kb("service_acc_manager", lang_code))

    await add_to_waiting_cbck_buffer(conn, cbck_message)

    await state.clear()
    await conn.close()

@admin_router.callback_query(CallbackArgFilter("detach_support_acc"))
@admin_router.callback_query(CallbackArgFilter("detach_head_acc"))
async def attach_acc(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    split = query.data.split("!")
    task = split[0]
    acc_id = int(split[1])

    if split == "detach_support_acc":
        await reset_moderator(acc_id, conn)

    await conn.execute("UPDATE accounts SET tg_user_id = NULL, login = NULL, language_code = NULL, blocking = NULL, show_award_notifications = NULL WHERE id = $1", acc_id)

    await query.message.edit_text(languages[lang_code]["answers"]["admin_router"]["acc_detached"])
    await query.message.edit_reply_markup(reply_markup=back_kb("view_support_acc!" + str(acc_id), lang_code))

    await conn.close() 