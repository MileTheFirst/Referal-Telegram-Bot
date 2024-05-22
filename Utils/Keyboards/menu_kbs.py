from aiogram.utils.keyboard import InlineKeyboardBuilder,ReplyKeyboardBuilder
from Sources.files import languages
import os

def user_main_menu_kb(lang_code: str, show_find_products_but = True):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["view_ref_s"], callback_data="view_ref_stat")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["my_catalogs"], callback_data="my_catalogs")
    if show_find_products_but:
        builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["search_products"], callback_data="search_products")
    builder.button(text=languages[lang_code]["keyboards"]["user_router"]["user_main_menu"]["tariffs"],  callback_data="tariffs")
    builder.button(text=languages[lang_code]["keyboards"]["user_router"]["user_main_menu"]["withdrawal"],  callback_data="withdrawal")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["account"], callback_data="account")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["support"], url=os.getenv("SUPPORT_URL"))
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["manual"], url=os.getenv("MANUAL_URL"))
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["rules"], url=os.getenv("RULES_URL"))
    builder.adjust(1)
    return builder.as_markup()

def old_base_acc_menu(lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["base_acc_menu"]["language"], callback_data="language")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_menu_kb(lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["admin_main_menu"]["service_acc_man"], callback_data="service_acc_manager")
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["admin_main_menu"]["technical_menu"], callback_data="technical_menu")
    builder.button(text=languages[lang_code]["keyboards"]["admin_router"]["admin_main_menu"]["s_l_menu"], callback_data="stat_lists_menu")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["my_catalogs"], callback_data="my_catalogs")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["search_products"], callback_data="search_products")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["account"], callback_data="account")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["rules"], url=os.getenv("RULES_URL"))
    builder.adjust(1)
    return builder.as_markup()

def support_main_menu_kb(lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["support_router"]["support_main_menu"]["moderate_catalogs"], callback_data="moderate_catalogs")
    builder.button(text=languages[lang_code]["keyboards"]["support_router"]["support_main_menu"]["moderate_withdrawals"], callback_data="moderate_withdrawals")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["account"], callback_data="account")
    builder.button(text=languages[lang_code]["keyboards"]["main_menu"]["rules"], url=os.getenv("RULES_URL"))
    builder.adjust(1)
    return builder.as_markup()



