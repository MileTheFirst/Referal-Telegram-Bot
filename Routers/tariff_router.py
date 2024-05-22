from aiogram import Router, types, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.often_kbs import back_kb, cancel_inline_kb
from Utils.Keyboards.special_kbs import gen_ref_link_kb, gened_ref_link_kb
from Utils.Keyboards.tariff_kbs import tariff_kb, choose_payment_method_kb, payment_confirmation_kb
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from Utils.Keyboards.catalogs_products_kbs import my_catalogs_menu_kb, my_product_menu_kb
from States.auth_states import InvitedRegForm
from States.tariff_states import BuyTariffForm
from Filters.filters import CallbackArgFilter, StatesFilter
from aiogram.utils.media_group import MediaGroupBuilder
from Utils.Methods.complect_ref_stat import complect_ref_stat
from Utils.Methods.tariff_upd import add_to_tariff_buffer, activate_in_tariff_buffer
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, delete_cbck_message
from datetime import timedelta
from Utils.Methods.awarding import awarding
from Sources.files import languages
import os
import json


tariff_router = Router()

tariff_router.message.filter(MagicData(F.is_auth.is_(True)))
tariff_router.callback_query.filter(MagicData(F.is_auth.is_(True)))

@tariff_router.callback_query(F.data == "cancel_buy_tariff")
async def cancel_tariff_buy(query: CallbackQuery,  state: FSMContext, lang_code: str):
    await state.clear()
    await query.message.edit_text(languages[lang_code]["answers"]["tariff_router"]["cancel"]["buying_tariff"])
    await query.message.edit_reply_markup(reply_markup=back_kb("tariffs", lang_code))





@tariff_router.callback_query(CallbackArgFilter("view_tariff"))
async def view_tariff(query: CallbackQuery, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    tariff = query.data.split("!")[1]

    tariff_info = await conn.fetchrow("SELECT * FROM tariff_params WHERE tariff = $1", tariff)

    text = languages[lang_code]["texts"]["tariff_text"]["tariff"] + languages[lang_code]["texts"]["tariffs"][tariff] + "\n"

    text += languages[lang_code]["texts"]["tariff_text"]["descriptions"][tariff] + "\n"

    if tariff_info['price_p_m'] != None:
        text += languages[lang_code]["texts"]["tariff_text"]["price_p_m"] + str(tariff_info['price_p_m']) + "\n"
    else:
        text += languages[lang_code]["texts"]["tariff_text"]["price_p_m"] + str(languages[lang_code]["texts"]["tariff_text"]["free"]) + "\n"

    if tariff_info['price_p_y'] != None:
        text += languages[lang_code]["texts"]["tariff_text"]["price_p_y"] + str(tariff_info['price_p_y']) + "\n"
    else:
        text += languages[lang_code]["texts"]["tariff_text"]["price_p_y"] + str(languages[lang_code]["texts"]["tariff_text"]["free"]) + "\n"


    user_id = await conn.fetchval("SELECT id FROM accounts WHERE tg_user_id = $1", query.from_user.id)
    tariff_buffer_info = await conn.fetchrow("SELECT * FROM tariff_buffer WHERE user_id = $1 AND tariff = $2", user_id, tariff) 

    show_buy_but = False
    show_activate_button = False

    #print(tariff_buffer_info)

    if tariff_buffer_info != None:
        if tariff_buffer_info["is_active"] == True:
            if tariff != "base":
                remains: timedelta = tariff_buffer_info["remains"]
                text += languages[lang_code]["texts"]["tariff_text"]["remains"]
                text += str(remains.days) + languages[lang_code]["texts"]["date_text"]["days"] + str(remains.seconds // 3600) + languages[lang_code]["texts"]["date_text"]["hours"] + str((remains.seconds // 60) % 60) + languages[lang_code]["texts"]["date_text"]["mins"] + "\n"
        else:
            show_activate_button = True
    elif tariff != "base":
        show_buy_but = True

    await query.message.edit_text(text)
    await query.message.edit_reply_markup(reply_markup=tariff_kb(tariff, show_buy_but, show_activate_button, lang_code))
    await conn.close()

#---------------------------------
    
@tariff_router.callback_query(CallbackArgFilter("buy_tariff"))
async def buy_tariff(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    tariff = query.data.split("!")[1]
    term = query.data.split("!")[2]

    price = 0
    if term == "month":
        price = await conn.fetchval("SELECT price_p_m FROM tariff_params WHERE tariff = $1", tariff)
    else:
        price = await conn.fetchval("SELECT price_p_y FROM tariff_params WHERE tariff = $1", tariff)

    await state.update_data({"tariff": tariff})
    await state.update_data({"price": price})
    await state.update_data({"term": term})
    await state.set_state(BuyTariffForm.tariff_payment_method)

    text = languages[lang_code]["answers"]["tariff_router"]["buy_tariff_1"] + languages[lang_code]["texts"]["tariffs"][tariff] + "\n"
    text += languages[lang_code]["answers"]["tariff_router"]["buy_tariff_2"]
    await query.message.edit_text(text)
    await query.message.edit_reply_markup(reply_markup=choose_payment_method_kb(lang_code))

    await conn.close()
    

@tariff_router.callback_query(BuyTariffForm.tariff_payment_method)
async def chosen_tarif_payment_method(query: CallbackQuery, state: FSMContext, lang_code: str):
    conn = await asyncpg.connect(**connection_params)
    data = await state.get_data()
    if query.data == "bonuses":
        await state.set_state(BuyTariffForm.tariff_bonuses_buy_confirm)
        bonuses = await conn.fetchval("SELECT bonuses FROM accounts WHERE tg_user_id = $1", query.from_user.id)
        text = languages[lang_code]["texts"]["acc_text"]["your_bonuses"] + str(bonuses) + "\n"
        text += languages[lang_code]["texts"]["tariff_text"]["tariff:"] + languages[lang_code]["texts"]["tariffs"][data['tariff']] + "\n"
        text += languages[lang_code]["texts"]["tariff_text"]["price"] + str(data['price'])

        await query.message.edit_text(text)
        if bonuses >= data['price']:
            await query.message.edit_reply_markup(reply_markup=payment_confirmation_kb(lang_code))
        else:
            await query.message.edit_reply_markup(reply_markup=back_kb("view_tariff!" + data["tariff"], lang_code))
    else:
        await state.set_state(BuyTariffForm.tariff_other_buy_confirm)
        cbck_messages = []
        send_invoice_mess = await query.message.answer_invoice(title=languages[lang_code]["texts"]["invoice_buy_tariff_text"]["title"] + data["tariff"],
                                           description=languages[lang_code]["texts"]["tariff_text"]["descriptions"][data["tariff"]],
                                           #payload=data["tariff"]+"$"+data["term"]+"$"+data["price"],
                                           payload=json.dumps(data),
                                           provider_token=os.getenv('PROVIDER_TOKEN'),
                                           currency= 'rub', 
                                           prices= [
                                               LabeledPrice(label=languages[lang_code]["texts"]["tariff_text"]["price"], amount=data["price"] * 100)
                                           ],
                                           provider_data=json.dumps({"receipt": {
                                               "items": [
                                                {
                                                    "description": data["tariff"] + "_" + data["term"] + "days",
                                                    "quantity": "1.00",
                                                    "amount": {
                                                        "value": str(float(data["price"])),
                                                        "currency": "RUB"
                                                    },
                                                    "vat_code": 1
                                                }
                                               ]
                                           }}),
                                           start_parameter="bot",
                                           need_email=True, 
                                           need_phone_number=True,
                                           send_email_to_provider=True,
                                           send_phone_number_to_provider=True
                                           )
        cbck_messages.append(send_invoice_mess)
        cbck_messages.append(await query.message.answer(languages[lang_code]["answers"]["tariff_router"]["cancel_buy_tariff"], reply_markup=cancel_inline_kb("cancel_buy_tariff", lang_code)))
        
        for mess in cbck_messages:
            await add_to_waiting_cbck_buffer(conn, mess)
        await delete_cbck_message(conn, query.message)
    await conn.close()



# @tariff_router.message(F.successuf_payment)
# async def successuf_payment(message: Message, lang_code: str):

@tariff_router.message(F.successful_payment)
@tariff_router.callback_query(BuyTariffForm.tariff_bonuses_buy_confirm, F.data == "confirm_buy") 
async def tariff_buy_confirm(query: CallbackQuery | Message, state: FSMContext, bot: Bot, lang_code: str):
    #print("SUCCESSFUL PAYMNENT:")
    conn = await asyncpg.connect(**connection_params)
    try: 
        data = {}
        if isinstance(query, CallbackQuery):
            data = await state.get_data()
        else:
            data = json.loads(query.successful_payment.invoice_payload)
            
        user_info = await conn.fetchrow("SELECT id, referer_id, blocking, bonuses FROM accounts WHERE tg_user_id = $1", query.from_user.id)

        term = timedelta(days=31)
        if data["term"] == "year":
            term = timedelta(days=365)

        

        if await add_to_tariff_buffer(user_info["id"], term, conn, tariff=data["tariff"]) == True:
            if isinstance(query, CallbackQuery):
                if user_info["bonuses"] >= float(data["price"]):
                    await conn.execute("UPDATE accounts SET bonuses = bonuses - $1 WHERE id = $2", float(data["price"]), user_info["id"])
                    await query.message.edit_text(languages[lang_code]["answers"]["tariff_router"]["tariff_bought"])
            elif isinstance(query, Message):
                #print(query.successful_payment.model_dump())
                cbck_message = await query.answer(languages[lang_code]["answers"]["tariff_router"]["tariff_bought"], reply_markup=back_kb("view_tariff!" + data["tariff"], lang_code))
                await add_to_waiting_cbck_buffer(conn, cbck_message)

            await awarding(user_info["referer_id"], data["price"]*0.05, 1, conn, bot)
            await activate_in_tariff_buffer(user_info["id"], conn, data["tariff"])
        else:
            raise Exception()
    except Exception as e: 
        print(e)
        print(e.__traceback__)
        if isinstance(query, CallbackQuery):
            await query.message.edit_text(languages[lang_code]["answers"]["tariff_router"]["error"]["buying_tariff"])
        elif isinstance(query, Message):
            cbck_message = await query.answer(languages[lang_code]["answers"]["tariff_router"]["error"]["buying_tariff"], reply_markup=back_kb("view_tariff!" + data["tariff"], lang_code))
            await add_to_waiting_cbck_buffer(conn, cbck_message)
    finally:
        if isinstance(query, CallbackQuery):
            await query.message.edit_reply_markup(reply_markup=back_kb("view_tariff!" + data["tariff"], lang_code))
        await state.clear()
        await conn.close()


@tariff_router.callback_query(CallbackArgFilter("activate_tariff"))
async def activate_tariff(query: CallbackQuery, lang_code: str):
    tariff = query.data.split("!")[1]
    conn = await asyncpg.connect(**connection_params)

    user_info = await conn.fetchrow("SELECT id, blocking FROM accounts WHERE tg_user_id = $1", query.from_user.id)

    if user_info["blocking"] == "blocked":
        if tariff == "vip":
            await conn.execute("UPDATE accounts SET blocking = NULL WHERE id = $1", user_info["id"])
    

    await activate_in_tariff_buffer(user_info["id"], conn, tariff)

    await query.message.edit_text(languages[lang_code]["answers"]["tariff_router"]["tariff_activated"])
    await query.message.edit_reply_markup(reply_markup=back_kb("main_menu", lang_code))

    await conn.close()
