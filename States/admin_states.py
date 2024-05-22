from aiogram.fsm.state import State, StatesGroup

class AttachAccForm(StatesGroup):
    attaching_acc_id = State()

class FilterWithdrawalsForm(StatesGroup):
    withdrawals_filter = State()

class FilterModerationsForm(StatesGroup):
    moderations_filter = State()

class DbQueryForm(StatesGroup):
    db_query = State()

class CustomNotifyForm(StatesGroup):
    custom_message = State()