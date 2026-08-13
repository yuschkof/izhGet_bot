import os
import re
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
async def process_admin_message(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): 
        return

    # Сохраняем необходимые данные для пересылки
    is_text = bool(message.text)
    
    await state.update_data(
        msg_id=message.message_id, 
        chat_id=message.chat.id,
        is_text=is_text,
        html_text=message.html_text if is_text else (message.html_text if message.caption else None)
    )

    # Показываем превью
    await message.answer("Вот так будет выглядеть сообщение:")
    
    try:
        if is_text:
            await bot.send_message(chat_id=message.chat.id, text=message.html_text, parse_mode="HTML")
        else:
            await bot.copy_message(chat_id=message.chat.id, from_chat_id=message.chat.id, message_id=message.message_id)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при формировании превью: {e}")
    
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
    is_text = data.get('is_text', False)
    html_text = data.get('html_text')
    
    users = db.get_all_users()
    
    await call.message.edit_text(f"🚀 Начинаю рассылку на {len(users)} пользователей...")
    
    success_count = 0
    block_count = 0
    
    for user_id in users:
        try:
            if is_text and html_text:
                await bot.send_message(chat_id=user_id, text=html_text, parse_mode="HTML")
            else:
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

@router.message(Command("reply"))
async def cmd_reply(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    parts = message.html_text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("⚠️ Использование: <code>/reply ID текст</code>", parse_mode="HTML")
        return
        
    user_id = parts[1]
    text = parts[2]
    
    try:
        await bot.send_message(user_id, f"👨‍💻 <b>Ответ от разработчика:</b>\n\n{text}", parse_mode="HTML")
        await message.answer("✅ Ответ отправлен.")
    except Exception as e:
        await message.answer(f"🚫 Ошибка при отправке: {e}")

@router.message(F.reply_to_message)
async def admin_reply_handler(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    # Пытаемся достать ID из сообщения, на которое отвечает админ
    original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    
    match = re.search(r"ID:\s*(\d+)", original_text)
    if not match:
        return # Ответили на какое-то другое сообщение
        
    user_id = int(match.group(1))
    
    try:
        if bool(message.text):
            await bot.send_message(user_id, f"👨‍💻 <b>Ответ от разработчика:</b>\n\n{message.html_text}", parse_mode="HTML")
        else:
            await bot.send_message(user_id, "👨‍💻 <b>Ответ от разработчика:</b>", parse_mode="HTML")
            await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            
        await message.answer("✅ Ответ отправлен.")
    except Exception as e:
        await message.answer(f"🚫 Ошибка при отправке: {e}")