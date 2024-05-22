from aiogram.fsm.state import State, StatesGroup

class WithdrawalForm(StatesGroup):
    withdrawal_amount = State()
    withdrawal_bank_card_number = State()