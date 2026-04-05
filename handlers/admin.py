import os
import asyncio
from dotenv import load_dotenv
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db.db as db

router = Router()

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

class AdminState(StatesGroup):
    waiting_for_message = State()
    confirm_send = State()

# Фильтр: проверяем, что пишет именно Админ
def is_admin(user_id):
    return int(user_id) == ADMIN_ID

# --- Клавиатуры для админки ---
def get_admin_confirm_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="admin_send")
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    builder.adjust(2)
    return builder.as_markup()

# --- Хендлеры ---

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return

    await message.answer("📢 <b>Режим рассылки</b>\n\nПришлите сообщение...")
    await state.set_state(AdminState.waiting_for_message)

@router.message(AdminState.waiting_for_message)
async def process_admin_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): 
        return

    # Сохраняем ID сообщения и ID чата, чтобы потом скопировать его
    # Мы не сохраняем текст, а копируем объект сообщения целиком
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)

    # Показываем превью (копируем админу его же сообщение)
    await message.answer("Вот так будет выглядеть сообщение:")
    await message.send_copy(chat_id=message.chat.id)
    
    await message.answer("Отправляем всем?", reply_markup=get_admin_confirm_kb())
    await state.set_state(AdminState.confirm_send)

@router.callback_query(AdminState.confirm_send, F.data == "admin_cancel")
async def cancel_broadcast(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Рассылка отменена.")

@router.callback_query(AdminState.confirm_send, F.data == "admin_send")
async def start_broadcast(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_id = data['msg_id']
    from_chat_id = data['chat_id']
    
    users = db.get_all_users()
    
    await call.message.edit_text(f"🚀 Начинаю рассылку на {len(users)} пользователей...")
    
    success_count = 0
    block_count = 0
    
    for user_id in users:
        try:
            # copy_message позволяет отправлять любые медиа
            await bot.copy_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=msg_id)
            success_count += 1
            # Небольшая пауза, чтобы не упереться в лимиты Телеграма (30 сообщ/сек)
            await asyncio.sleep(0.05) 
            
        except Exception as e:
            # Обычно ошибка возникает, если юзер заблокировал бота
            block_count += 1
    
    await call.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Доставлено: {success_count}\n"
        f"Заблокировали бота (не доставлено): {block_count}"
    )
    await state.clear()