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
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu, support_main_menu_kb
from Utils.Keyboards.catalogs_products_kbs import my_catalogs_menu_kb, my_product_menu_kb
from States.auth_states import InvitedRegForm
from States.operation_states import WithdrawalForm
from Filters.filters import CallbackArgFilter
from aiogram.utils.media_group import MediaGroupBuilder
from Utils.Methods.complect_ref_stat import complect_ref_stat

from Utils.Methods.mailing import permanent_mailing_task
from Utils.Methods.tariff_upd import permanent_tariff_update_task
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from Filters.filters import RoleFilter
from Sources.files import languages
from Utils.Methods.moderation import find_free_moderator


from Sources.files import set_last_tariff_check_date

import os

from datetime import datetime

withdrawal_router = Router()

withdrawal_router.message.filter(MagicData(F.is_auth.is_(True)))
withdrawal_router.callback_query.filter(MagicData(F.is_auth.is_(True)))


@withdrawal_router.callback_query(F.data == "cancel_creating_withdrawal_request")
async def cancel_creating_withdrawal_request(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    await state.clear()

    await query.message.edit_text(languages[lang_code]["answers"]["withdrawal_router"]["cancel"]["creating_withdrawal"])
    await query.message.edit_reply_markup(reply_markup=back_kb("withdrawal", lang_code))

    await conn.close()


@withdrawal_router.callback_query(F.data == "withdrawal")
async def withdrawal(query: CallbackQuery,  lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    acc_info = await conn.fetchrow("SELECT bonuses, id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    bonuses = acc_info["bonuses"]

    existing_withdrawal = await conn.fetchrow("SELECT * FROM withdrawal_list WHERE user_id = $1 AND bank_card_number IS NOT NULL", acc_info["id"])

    if existing_withdrawal == None:
        builder = InlineKeyboardBuilder()
        builder.button(text=languages[lang_code]["keyboards"]["often"]["create"], callback_data="create_withdrawal_request")
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
        builder.adjust(1)
        await query.message.edit_text(text=languages[lang_code]["answers"]["withdrawal_router"]["no_withdrawals"])
        await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    else:
        text = languages[lang_code]["texts"]["withdrawal_text"]["your_withdrawal"] + "\n"
        text += languages[lang_code]["texts"]["acc_text"]["bonuses"] + str(bonuses) + "\n"
        text += languages[lang_code]["texts"]["withdrawal_text"]["id"] + str(existing_withdrawal["id"]) + "\n"
        text += languages[lang_code]["texts"]["withdrawal_text"]["amount"] + str(existing_withdrawal["amount"]) + "\n"
        text += languages[lang_code]["texts"]["withdrawal_text"]["bank_card_number"] + existing_withdrawal["bank_card_number"] + "\n"

        builder = InlineKeyboardBuilder()
        builder.button(text=languages[lang_code]["keyboards"]["often"]["del"], callback_data="del_withdrawal!"+str(existing_withdrawal["id"]))
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
        builder.adjust(1)
        
        cbck_mess =await query.message.answer(text=text, reply_markup=builder.as_markup())
        
        await add_to_waiting_cbck_buffer(conn, cbck_mess)
        await delete_cbck_message(conn, query.message)

    await conn.close()

@withdrawal_router.callback_query(F.data == "create_withdrawal_request")
async def start_withdrawal(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    acc_info = await conn.fetchrow("SELECT bonuses, id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    bonuses = acc_info["bonuses"]

    MIN_WITHDRAWAL_AMOUNT = await conn.fetchval("SELECT MIN_WITHDRAWAL_AMOUNT FROM config LIMIT 1")

    text = languages[lang_code]["texts"]["withdrawal_text"]["withdrawal"] + "\n"
    text += languages[lang_code]["texts"]["acc_text"]["bonuses"] + str(bonuses) + "\n"
    text += languages[lang_code]["answers"]["withdrawal_router"]["write_amount"] + "\n"
    text += languages[lang_code]["texts"]["withdrawal_text"]["min_amount"] + str(MIN_WITHDRAWAL_AMOUNT)
    cbck_mess =await query.message.answer(text=text, reply_markup=cancel_inline_kb("cancel_creating_withdrawal_request", lang_code))
    
    await state.update_data({"bonuses": bonuses})
    await state.set_state(WithdrawalForm.withdrawal_amount)

    await add_to_waiting_cbck_buffer(conn, cbck_mess)
    await delete_cbck_message(conn, query.message)

    await conn.close()

@withdrawal_router.message(WithdrawalForm.withdrawal_amount, F.text)
async def withdrawal_amount(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    amount = float(html.quote(message.text))
    data = await state.get_data()

    bonuses = data["bonuses"]

    MIN_WITHDRAWAL_AMOUNT = await conn.fetchval("SELECT MIN_WITHDRAWAL_AMOUNT FROM config LIMIT 1")

    if MIN_WITHDRAWAL_AMOUNT <= amount <= bonuses:
        await state.update_data({"amount": amount})

        await state.set_state(WithdrawalForm.withdrawal_bank_card_number)

        cbck_mess = await message.answer(text=languages[lang_code]["answers"]["withdrawal_router"]["write_bank_card_number"], reply_markup=cancel_inline_kb("cancel_creating_withdrawal_request", lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_mess)
    else:
        cbck_mess = await message.answer(text=languages[lang_code]["answers"]["withdrawal_router"]["not_correct"]["amount"], reply_markup=cancel_inline_kb("cancel_creating_withdrawal_request", lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_mess)  

    await conn.close()


@withdrawal_router.message(WithdrawalForm.withdrawal_bank_card_number, F.text)
async def withdrawal_amount(message: Message, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)

    bank_card_number = html.quote(message.text)
    data = await state.get_data()

    amount = data["amount"]
    bonuses = data["bonuses"]

    MIN_WITHDRAWAL_AMOUNT = await conn.fetchval("SELECT MIN_WITHDRAWAL_AMOUNT FROM config LIMIT 1")


    if MIN_WITHDRAWAL_AMOUNT <= amount <= bonuses:
        pre_moderators = await conn.fetch("SELECT * FROM accounts WHERE role = 'support' and tg_user_id IS NOT NULL")

        moderator = await find_free_moderator(pre_moderators, conn)

        user_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", message.from_user.id)
        await conn.execute("INSERT INTO withdrawal_list (user_id, bank_card_number, moderator_id, amount) VALUES ($1, $2, $3, $4)", user_id, bank_card_number, moderator["id"], amount)

        cbck_mess = await message.answer(text=languages[lang_code]["answers"]["withdrawal_router"]["request_added"], reply_markup=back_kb("withdrawal", lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_mess)
    else:
        cbck_mess = await message.answer(text=languages[lang_code]["answers"]["withdrawal_router"]["not_correct"]["amount"], reply_markup=cancel_inline_kb("cancel_creating_withdrawal_request", lang_code))
        await add_to_waiting_cbck_buffer(conn, cbck_mess)  

    await state.clear()

    await conn.close()


@withdrawal_router.callback_query(CallbackArgFilter("del_withdrawal"))
async def del_withdrawal(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    withdrawal_id = int(query.data.split("!")[1])

    if await conn.fetchval("SELECT moderation_date FROM withdrawal_list WHERE id = $1", withdrawal_id) == None:
        await conn.execute("DELETE FROM withdrawal_list WHERE id = $1", withdrawal_id)
        await query.message.edit_text(languages[lang_code]["answers"]["withdrawal_router"]["del"])
    else:
        await query.message.edit_text(languages[lang_code]["answers"]["errors"]["smth"])

    await query.message.edit_reply_markup(reply_markup=back_kb("withdrawal", lang_code))

    await conn.close()