from aiogram.fsm.state import State, StatesGroup

class AddCatalogForm(StatesGroup):
    add_catalog_name = State()

class EditCatalogForm(StatesGroup):
    edit_catalog_photo = State()

class DelCatalogForm(StatesGroup):
    del_catalog_name = State()


class AddProductForm(StatesGroup):
    add_product_cat = State()
    add_product_name = State()
    add_product_desc = State()
    add_product_photo = State()

class EditMailingForm(StatesGroup):
    edit_next_mailing_date = State()
    edit_mailing_interval = State()

class EditProductForm(StatesGroup):
    edit_product_name = State()
    edit_product_cat = State()
    edit_product_desc = State()
    edit_add_product_photo = State()
    