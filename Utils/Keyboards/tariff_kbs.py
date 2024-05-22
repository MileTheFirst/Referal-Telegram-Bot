from aiogram.utils.keyboard import InlineKeyboardBuilder,ReplyKeyboardBuilder
from datetime import timedelta
from Sources.files import languages

def tariffs_kb(tariffs, lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["texts"]["tariffs"]["base"], callback_data="view_tariff!base")
    for tariff in tariffs:
        if tariff["tariff"] != "base":
            builder.button(text=languages[lang_code]["texts"]["tariffs"][tariff["tariff"]], callback_data="view_tariff!"+tariff["tariff"])
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def tariff_kb(tariff, show_buy_but: bool, show_activate_button: bool, lang_code: str):
    builder = InlineKeyboardBuilder()
    if show_buy_but:
        builder.button(text=languages[lang_code]["keyboards"]["tariff_router"]["tariff_menu"]["buy_month"], callback_data="buy_tariff!" + tariff + "!" + "month")
        builder.button(text=languages[lang_code]["keyboards"]["tariff_router"]["tariff_menu"]["buy_year"], callback_data="buy_tariff!" + tariff + "!" + "year")
    elif show_activate_button:
        builder.button(text=languages[lang_code]["keyboards"]["tariff_router"]["tariff_menu"]["activate"], callback_data="activate_tariff!" + tariff)
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="tariffs")
    builder.adjust(1)
    return builder.as_markup()
    


def choose_payment_method_kb(lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["tariff_router"]["pay_method_menu"]["bonuses"], callback_data="bonuses")
    builder.button(text=languages[lang_code]["keyboards"]["tariff_router"]["pay_method_menu"]["others"], callback_data="other")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_buy_tariff")
    builder.adjust(1)
    return builder.as_markup()

def payment_confirmation_kb(lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["tariff_router"]["buy"], callback_data="confirm_buy")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data="cancel_buy_tariff")
    builder.adjust(1)
    return builder.as_markup()