from aiogram.utils.keyboard import InlineKeyboardBuilder,ReplyKeyboardBuilder
from Sources.files import languages

def back_kb(cbck_data: str, lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data=cbck_data)
    return builder.as_markup()

def cancel_inline_kb(cbck_data: str, lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data=cbck_data)
    return builder.as_markup()

def edit_kb(cbck_data: str, lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["edit"], callback_data=cbck_data)
    return builder.as_markup()

def del_kb(cbck_data: str, lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["del"], callback_data=cbck_data)
    return builder.as_markup()