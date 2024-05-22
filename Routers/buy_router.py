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

buy_router = Router()

@buy_router.pre_checkout_query()
async def pre_checkout_query_f(pre_checkout_query: PreCheckoutQuery, state: FSMContext, bot: Bot, lang_code: str):
    # print("Test pre_ckeckout_query")
    # print(pre_checkout_query.model_dump())
    await pre_checkout_query.answer(ok=True)
    # print("Test pre_ckeckout_query True")