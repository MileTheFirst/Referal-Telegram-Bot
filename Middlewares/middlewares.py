from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery
from typing import Any, Callable, Dict, Awaitable
from aiogram.types import TelegramObject, Message, Update
from Sources.db import connection_params
from Sources.files import languages
import asyncpg
from Utils.Methods.message_buffer import add_to_waiting_cbck_buffer
from datetime import datetime, timedelta
import asyncio

class DeleteWaitingCbckMessageMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user_id = data["event_from_user"].id
        bot: Bot = data["bot"]

        #event: Update
        conn = await asyncpg.connect(**connection_params)

        message = event.message
        query = event.callback_query

        waiting_cbck_messages = []
        
        if query != None:
            waiting_cbck_messages = await conn.fetch("SELECT * FROM waiting_cbck_buffer WHERE chat_id = $1 and message_id != $2", user_id, query.message.message_id)
        elif message != None:
            waiting_cbck_messages = await conn.fetch("SELECT * FROM waiting_cbck_buffer WHERE chat_id = $1", user_id)
        
        try:
            for waiting_cbck_message in waiting_cbck_messages:
                #print(waiting_cbck_message)
                await conn.execute("DELETE FROM waiting_cbck_buffer WHERE id = $1", waiting_cbck_message["id"])
                await bot.delete_message(waiting_cbck_message["chat_id"], waiting_cbck_message["message_id"])
        except Exception as e:
            print(e)
            print(e.__traceback__)
        finally:
            await conn.close()
            return await handler(event, data)
        
    


# class AddWaitingCbckMessageMiddleware(BaseMiddleware):
#     async def __call__(
#             self,
#             handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#             event: Message,
#             data: Dict[str, Any],
#     ) -> Any:
#         result = await handler(event, data)
#         if isinstance(result, Message):
#             conn = await asyncpg.connect(**connection_params)
#             await add_to_waiting_cbck_buffer()
#             await conn.close()
    
class lang_code_middleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user_id = data["event_from_user"].id

        conn = await asyncpg.connect(**connection_params)

        lang_code = await conn.fetchval("SELECT language_code FROM accounts WHERE tg_user_id = $1", user_id)

        if lang_code == None:
            lang_code = "en"
            language_code = data["event_from_user"].language_code
            if language_code in languages:
                lang_code =  language_code

        data["lang_code"] = lang_code

        return await handler(event, data)


# class lock_callback_middleware(BaseMiddleware):
#     async def __call__(
#             self,
#             handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#             event: CallbackQuery,
#             data: Dict[str, Any],
#     ) -> Any:
#         if datetime.now() + timedelta(hours=int(os.getenv("UTC_HOURS"))) - event.message.date < timedelta(hours=48):
#             return await handler(event, data)
#         else:
#             bot: Bot = data["bot"]
#             await event.message.copy_to(event.message.chat.id)
            