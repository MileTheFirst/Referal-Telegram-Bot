from aiogram.utils.keyboard import InlineKeyboardBuilder,ReplyKeyboardBuilder
from Sources.files import languages

def sign_in_or_up_kb(): #xxxxxxxxxxx
    builder = InlineKeyboardBuilder()
    builder.button(text="Sign in", callback_data="sign_in")
    builder.button(text="Sign up", callback_data="sign_up")
    builder.adjust(1)
    return builder.as_markup()

def gen_ref_link_kb(lang_code: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["user_router"]["ref_link"]["gen"], callback_data="gen_ref_link")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def gened_ref_link_kb(lang_code: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["view"], callback_data="view_ref_stat")
    builder.adjust(1)
    return builder.as_markup()
