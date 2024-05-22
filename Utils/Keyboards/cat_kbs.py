from aiogram.utils.keyboard import InlineKeyboardBuilder,ReplyKeyboardBuilder
from Sources.files import languages

def cats_in_cat_builder(categories: list, lang_code: str):
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=languages[lang_code]["words"]["categories"][category["name"]], callback_data="view_cat!"+str(category["id"]) + "!" + str(category["name"]))
    
    return builder

# def choose_cats_in_cat_kb(categories: list, parent_cat_id, parent_cat_name):
#     builder = InlineKeyboardBuilder()
#     for category in categories:
#         builder.button(text=category["name"], callback_data="view_cat!"+str(category["id"]) + "!" + str(category["name"]))
#     if parent_cat_id != None:
#         builder.button(text="Back", callback_data="view_cat!" + str(parent_cat_id) + "!" + parent_cat_name)
#     else:
#         builder.button(text="Cancel", callback_data="")
#     builder.adjust(1)
#     return builder.as_markup()

def choose_cat_kb(cat_id, cat_name, parent_cat_id, parent_cat_name):
    builder = InlineKeyboardBuilder()
    builder.button(text="Choose", callback_data="choose_cat!"+str(cat_id) + "!" + cat_name)
    builder.button(text="Back", callback_data="view_cat!" + str(parent_cat_id) + "!" + parent_cat_name)
    builder.adjust(1)
    return builder.as_markup()