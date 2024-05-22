from aiogram.fsm.state import State, StatesGroup

class BuyTariffForm(StatesGroup):
    tariff_payment_method = State()
    tariff_bonuses_buy_confirm = State()
    tariff_other_buy_confirm = State()