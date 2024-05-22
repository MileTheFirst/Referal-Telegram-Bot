from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
from Sources.files import languages
from States.auth_states import InvitedRegForm
import asyncpg
import hashlib 
from Utils.Keyboards.special_kbs import sign_in_or_up_kb
from Filters.filters import StatesFilter
from Utils.Methods.complect_ref_stat import complect_ref_stat
from Utils.Methods.awarding import awarding
from Utils.Methods.tariff_upd import add_to_tariff_buffer, activate_in_tariff_buffer
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, del_from_waiting_cbck_buffer, delete_cbck_message
from datetime import timedelta, datetime
import os

auth_router = Router()

auth_router.message.filter(MagicData(F.is_auth.is_(False)))
auth_router.callback_query.filter(MagicData(F.is_auth.is_(False)))


# @auth_router.callback_query(F.data == "cancel_reg_user")
# async def cancel_reg_user(query: CallbackQuery, lang_code: str):
#     conn = await asyncpg.connect(**connection_params)
#     await query.message.answer(text=languages[lang_code]["answers"]["auth_routers"]["cancel"]["reg"])
#     await delete_cbck_message(conn, query.message)
#     await conn.close()

# @auth_router.callback_query(F.data == "cancel_reg_invited_user")
# async def cancel_reg_user(query: CallbackQuery, state: FSMContext, lang_code):
#     await state.clear()
#     conn = await asyncpg.connect(**connection_params)
#     await query.message.answer(text=languages[lang_code]["answers"]["auth_routers"]["cancel"]["reg_w_ref"])
#     await delete_cbck_message(conn, query.message)
#     await conn.close()

@auth_router.message(CommandStart())
async def new_invited_referal(message: Message, bot: Bot, lang_code: str):
    #print("start")
    mess_text = html.quote(message.text)
    split = mess_text.split(" ")

    ref_link = None
    identifier = None

    if len(split) > 1:
        args = split[1]
        # print(args)
        link_split = args.split("ref")

        # print("Link split: ")
        # print(link_split)

        if len(link_split) > 1:
            ref_link = link_split[1]

        if link_split[0] != "":
            identifier = link_split[0]
        

        # if arg.startswith("ref"):
        #     ref_link = arg[3:]
        # else:
        #     identifier = arg

    conn = await asyncpg.connect(**connection_params)

    referer_id = None

    if ref_link != None:
        referer_id = await conn.fetchval("SELECT id FROM accounts WHERE ref_link = $1", ref_link)
    else:
        pre_referers = await conn.fetch("SELECT id FROM accounts WHERE referer_id IS NULL and role = 'user'")
        last_min_count = None
        for pre_referer in pre_referers:
            ref_stat = await complect_ref_stat(pre_referer["id"], conn)
            if (last_min_count == None) or (ref_stat["full_count"] < last_min_count):
                last_min_count = ref_stat["full_count"]
                referer_id = pre_referer["id"]

    language_code = "en"
    if message.from_user.language_code in languages:
        language_code = message.from_user.language_code

    #print(language_code)
    if message.from_user.username != None:
        login = html.quote(message.from_user.username)
    else:
        login = html.quote(message.from_user.full_name)
    
    acc_id = await conn.fetchval('''
        INSERT INTO accounts (tg_user_id, login, role, referer_id, bonuses, language_code, source, show_award_notifications) VALUES ($1, $2, 'user', $3, $4, $5, $6, true) RETURNING id
        ''', message.from_user.id, login, referer_id, 0, language_code, identifier)

    await add_to_tariff_buffer(acc_id, None, conn)
    await add_to_tariff_buffer(acc_id, timedelta(days=14), conn, "advanced")
    await activate_in_tariff_buffer(acc_id, conn)

    await conn.execute("INSERT INTO logs (description, date) VALUES ($1, $2)", f"New account added. acc_id = {str(acc_id)}", datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))))

    await awarding(acc_id, 2.5, 0, conn, bot)

    await message.answer(text=languages[lang_code]["answers"]["auth_routers"]["reg_completed"]) #repKeyRem
    
    await conn.close()

#----------

# @auth_router.message(CommandStart(deep_link=False))
# async def new_user(message: Message, lang_code: str):
#     #print("without_deep_link")
#     conn = await asyncpg.connect(**connection_params)
    
#     referer_id = None

#     pre_referers = await conn.fetch("SELECT id FROM accounts WHERE referer_id IS NULL and role = 'user'")
#     last_min_count = None
#     for pre_referer in pre_referers:
#         ref_stat = await complect_ref_stat(pre_referer["id"], conn)
#         if (last_min_count == None) or (ref_stat["full_count"] < last_min_count):
#             last_min_count = ref_stat["full_count"]
#             referer_id = pre_referer["id"]

#     language_code = "en"
#     if message.from_user.language_code in languages:
#         language_code =  message.from_user.language_code
#     #print(language_code)
    
#     acc_id = await conn.fetchval('''
#         INSERT INTO accounts (tg_user_id, login, role, referer_id, bonuses, language_code) VALUES ($1, $2, 'user', $3, $4, $5) RETURNING id
#         ''', message.from_user.id, html.quote(message.from_user.full_name), referer_id, 0, language_code)

#     await add_to_tariff_buffer(acc_id, None, conn)
#     await activate_in_tariff_buffer(acc_id, conn)

#     await awarding(acc_id, 2.5, 0, conn)

#     await message.answer(text=languages[lang_code]["answers"]["auth_routers"]["reg_completed"]) #repKeyRem
    
#     await conn.close()


# @auth_router.callback_query(F.data == "reg_user")
# @auth_router.callback_query(F.data == "reg_invited_user", InvitedRegForm.confirm_inv_reg)
# async def sign_in_start(query: CallbackQuery, state: FSMContext, lang_code: str):
#     conn = await asyncpg.connect(**connection_params)
#     #print(query.data)

#     referer_id = None

#     if query.data == "reg_user":
#         pre_referers = await conn.fetch("SELECT id FROM accounts WHERE referer_id IS NULL and role = 'user'")
#         last_min_count = None
#         for pre_referer in pre_referers:
#             ref_stat = await complect_ref_stat(pre_referer["id"], conn)
#             if (last_min_count == None) or (ref_stat["full_count"] < last_min_count):
#                 last_min_count = ref_stat["full_count"]
#                 referer_id = pre_referer["id"]
#     else:
#         data = await state.get_data()
#         ref_link = data["ref_link"]
#         referer_id = await conn.fetchval("SELECT id FROM accounts WHERE ref_link = $1", ref_link)
        
#     #print(query.from_user.language_code)
#     language_code = "en"
#     if query.from_user.language_code in languages:
#         language_code =  query.from_user.language_code
#     #print(language_code)
    
#     acc_id = await conn.fetchval('''
#         INSERT INTO accounts (tg_user_id, login, role, referer_id, bonuses, language_code) VALUES ($1, $2, 'user', $3, $4, $5) RETURNING id
#         ''', query.from_user.id, html.quote(query.from_user.full_name), referer_id, 0, language_code)

#     await add_to_tariff_buffer(acc_id, None, conn)
#     await activate_in_tariff_buffer(acc_id, conn)

#     if query.data == "reg_invited_user":
#         await awarding(acc_id, 5, 0, conn)
#         await state.clear()

#     await query.message.answer(text=languages[lang_code]["answers"]["auth_routers"]["reg_completed"]) #repKeyRem
#     await delete_cbck_message(conn, query.message)

#     await conn.close()

