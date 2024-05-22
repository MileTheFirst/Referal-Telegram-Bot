from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from typing import Tuple
from aiogram import types
import asyncpg
from Sources.db import connection_params


class StatesFilter(BaseFilter):
    def __init__(self, all_states_names: Tuple[str, ...]):
        self.all_states_names = all_states_names
    
    async def __call__(self, message: types.Message, state: FSMContext):        
        return await state.get_state() in self.all_states_names
    

class CallbackArgFilter(BaseFilter):
    def __init__(self, arg: str):
        self.arg = arg

    async  def __call__(self, query: types.CallbackQuery):
        split = query.data.split("!")
        if split != None:
            return split[0] == self.arg
        return False
    

class RoleFilter(BaseFilter):
    def __init__(self, role: str):
        self.role = role

    async def __call__(self, update):
        tg_user_id = update.from_user.id

        conn = await asyncpg.connect(**connection_params)
        user_role = await conn.fetchval("SELECT role FROM accounts WHERE tg_user_id = $1", tg_user_id)

        result = user_role == self.role

        await conn.close()
        return result