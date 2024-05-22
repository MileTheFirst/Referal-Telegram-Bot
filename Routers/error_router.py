from aiogram import Router, types, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, MagicData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from Sources.db import connection_params
import asyncpg
import hashlib 
from Utils.Keyboards.menu_kbs import user_main_menu_kb, old_base_acc_menu
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer, delete_cbck_message
from States.auth_states import InvitedRegForm
from Sources.files import languages

error_router = Router()

@error_router.message(Command("menu"), MagicData(F.is_auth.is_(False)))
async def main_menu_cbq(message: Message, lang_code: str):
    await message.answer(text=languages[lang_code]["answers"]["error_router"]["h_t_log_in"])

@error_router.message(Command("start"), MagicData(F.is_auth.is_(True)))
async def already_start(message: Message, lang_code: str):
    await message.answer(text=languages[lang_code]["answers"]["error_router"]["already_started"])

@error_router.message()
async def query_not_processed(message: Message, lang_code: str):
    await message.answer(languages[lang_code]["answers"]["errors"]["query_not_processed"])

@error_router.callback_query()
async def cbck_query_not_processed(query: CallbackQuery, lang_code: str):
    await query.message.answer(languages[lang_code]["answers"]["errors"]["query_not_processed"])