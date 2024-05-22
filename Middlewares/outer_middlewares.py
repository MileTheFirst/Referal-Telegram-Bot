from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery
from typing import Any, Callable, Dict, Awaitable
from aiogram.types import TelegramObject
from Sources.db import connection_params
import asyncpg
from Files import buffer
from Sources.files import languages


class UserInfoAndBotBlockingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user_id = data["event_from_user"].id
        bot: Bot = data["bot"]

        conn = await asyncpg.connect(**connection_params)

        print(user_id)
        print(data)
        #print(event)
        user_info = await conn.fetchrow("SELECT role, language_code, blocking FROM accounts WHERE tg_user_id = $1", user_id)

        #print(user_info)
        
        if user_info != None:
            data["is_auth"] = True
            if event.message != None or event.callback_query != None:
                if user_info["blocking"] == "bot_kicked":
                    await conn.execute("UPDATE accounts SET blocking = NULL WHERE tg_user_id = $1", user_id)
        else: 
            data["is_auth"] = False
            print("is_auth = False")

        if buffer.bot_blocked == False or (user_info != None and user_info["role"] == "admin"):
            return await handler(event, data)
        else:
            await bot.send_message(chat_id=user_id, text=languages[user_info["language_code"]]["texts"]["notifications"]["bot_blocked"])
    


# class BotBlockingMiddleware(BaseMiddleware):
#     async def __init__(self):
#         conn = await asyncpg.connect(**connection_params)
#     async def __call__(
#             self,
#             handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#             event: TelegramObject,
#             data: Dict[str, Any],
#     ) -> Any:
#         user_id = data["event_from_user"].id
#         bot: Bot = data["bot"]

#         user_info = await self.conn.fetchrow("SELECT role, language_code FROM accounts WHERE tg_user_id = $1", user_id)

#         if buffer.bot_blocked == False or user_info["role"] == "admin":
#             return await handler(event, data)
#         else:
#             await bot.send_message(chat_id=user_id, text=languages[user_info["language_code"]]["texts"]["notifications"]["bot_blocked"])