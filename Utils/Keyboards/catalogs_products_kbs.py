from aiogram.utils.keyboard import InlineKeyboardBuilder,ReplyKeyboardBuilder
from Sources.files import languages

def my_catalogs_menu_kb(catalog_list: list[dict], lang_code: str):
    builder = InlineKeyboardBuilder()
    for catalog in catalog_list:
        builder.button(text=catalog["name"], callback_data= "view_my_catalog!" + str(catalog["id"]))
    builder.button(text=languages[lang_code]["keyboards"]["catalogs"]["add_catalog"], callback_data="add_catalog")
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def received_catalog_kb(catalog_id, catalog_name, lang_code: str, back_data: str = None):
    builder = InlineKeyboardBuilder()
    builder.button(text=catalog_name, callback_data="view_received_catalog!" + str(catalog_id))
    if back_data != None:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data=back_data)
    builder.adjust(1)
    return builder.as_markup()

#----------------
    

def products_menu_kb(product_list: list[dict], lang_code, back_data: str = None, cancel_data: str = None):
    builder = InlineKeyboardBuilder()
    for product in product_list:
        builder.button(text=product["name"], callback_data= "view_product!" + str(product["id"]))
    if back_data != None:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data=back_data)
    if cancel_data != None:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["cancel"], callback_data=cancel_data)
    builder.adjust(1)
    return builder.as_markup()

def received_products_in_catalog_menu_kb(product_list: list[dict], lang_code, back_data: str = None):
    builder = InlineKeyboardBuilder()
    for product in product_list:
        builder.button(text=product["name"], callback_data= "view_received_product!" + str(product["id"]))
    if back_data != None:
        builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data=back_data)
    builder.adjust(1)
    return builder.as_markup()

def product_menu_kb(back_data: str, lang_code): #xxxxxxxxxxxxxx
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data=back_data)
    builder.adjust(1)
    return builder.as_markup()

def my_product_menu_kb(product_id: int, catalog_id, lang_code):
    builder = InlineKeyboardBuilder()
    builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_product_menu"]["edit"], callback_data="edit_product!"+ str(product_id))
    builder.button(text=languages[lang_code]["keyboards"]["view_router"]["view_my_product_menu"]["delete"], callback_data="delete_product!" + str(product_id) + "!" + str(catalog_id))
    builder.button(text=languages[lang_code]["keyboards"]["often"]["back"], callback_data="view_my_catalog!" + str(catalog_id))
    builder.adjust(1)
    return builder.as_markup()

def received_product_menu_kb(product_id: int, catalog_id): #xxxxxxxxxxxxxxxxx
    pass

