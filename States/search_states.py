from aiogram.fsm.state import State, StatesGroup

class SearchProductsFilterForm(StatesGroup):
    search_products_category = State()
    search_products_query = State()
    search_products_result = State()