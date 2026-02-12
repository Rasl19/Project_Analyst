from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import pandas as pd
import os

import app.keyboards as kb
import app.questions as q

router = Router()

# Для хранения состояния пользователей
user_data = {}

# Функция для сохранения результатов в CSV
def save_results(user_id: int, full_name: str, username: str, score: int, total: int, status: bool):
    data = {
        'user_id': [user_id],
        'full_name': [full_name],
        'username': [username],
        'score': [score],
        'total': [total],
        'percentage': [round((score/total)*100, 2)],
        'status': [status],
    }
    
    df = pd.DataFrame(data)
    
    if not os.path.exists('results.csv'):
        df.to_csv('results.csv', index=False)
    else:
        df.to_csv('results.csv', mode='a', header=False, index=False)


@router.message(CommandStart())
async def cmd_start(message: Message):
    # Проверка на аттестован ли пользователь
    if os.path.exists('results.csv'):
        df = pd.read_csv('results.csv')
        user_results = df[df['user_id'] == message.from_user.id]

        if not user_results.empty:
            last_result = user_results.iloc[-1]
            if user_results['status'].any():
                await message.answer('Вы уже аттестованы ✅')
                return

    
    await message.answer(
        f'Привет, {message.from_user.full_name}!\n\n'
        'Я Телеграм Бот. И мне поручили провести твою аттестацию.\n'
        'Аттестация будет проходить в формате теста.\n'
        'Для успешного прохождения аттестации, необходимо ответить верно на 7 и более вопросов.\n'
        'Всего будет 10 вопросов\n\n'
        '/status - Статус аттестации (Аттестован/Не аттестован)'
    )
    await message.answer('Начнем?', reply_markup=kb.main)

# Статус аттестации
@router.message(Command('status'))
async def get_status(message: Message):
    if os.path.exists('results.csv'):
        df = pd.read_csv('results.csv')
        user_results = df[df['user_id'] == message.from_user.id]
        
        if not user_results.empty:
            last_result = user_results.iloc[-1]
            status = 'Аттестован ✅' if user_results['status'].any() else 'Не аттестован ❌'
            await message.answer(
                f"Ваш статус: {status}\n"
                f"Результат: {last_result['score']}/{last_result['total']} "
                f"({last_result['percentage']}%)"
            )
            return
    
    await message.answer("Вы еще не проходили аттестацию. Нажмите /start")

# Начало теста
@router.callback_query(F.data == 'test')
async def start_test(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id] = {
        'current_question': 1,
        'score': 0,
        'total_questions': len(q.TEST_1),
        'full_name': callback.from_user.full_name,
        'username': callback.from_user.username,
        'status': False,
    }
    await callback.answer()  # Подтверждаем обработку callback
    await ask_question(callback.message, user_id)

# Задать вопрос
async def ask_question(message: Message, user_id: int):
    question_num = user_data[user_id]['current_question']
    total_questions = user_data[user_id]['total_questions']
    
    if question_num > total_questions:
        # Тест завершен
        percentage = (user_data[user_id]['score'] / total_questions) * 100
        status = True if percentage >= 70 else False
        
        # Сохраняем результаты
        save_results(
            user_id=user_id,
            full_name=user_data[user_id]['full_name'],
            username = user_data[user_id]['username'],
            score=user_data[user_id]['score'],
            total=total_questions,
            status=status,
        )
        
        await message.edit_text(
            f"Тест завершен!\n"
            f"Результат: {user_data[user_id]['score']}/{total_questions}\n"
            f"Статус: {'Аттестован ✅' if status else 'Не аттестован ❌'}\n\n"
            + ("Поздравляю!" if status else "Для повторного прохождения нажмите /start")
        )
        return
    
    # Продолжаем тест
    question = q.TEST_1[question_num]
    builder = InlineKeyboardBuilder()
    
    for idx, option in enumerate(question['options']):
        builder.button(text=option, callback_data=str(idx))
    
    builder.adjust(1)
    
    await message.edit_text(
        f"Вопрос {question_num}/{total_questions}:\n"
        f"{question['question']}",
        reply_markup=builder.as_markup()
    )

# Обработка ответа
@router.callback_query(lambda c: c.data.isdigit())
async def process_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    question_num = user_data[user_id]['current_question']
    
    # Проверяем, что вопрос существует
    if question_num not in q.TEST_1:
        await callback.answer("Тест уже завершен!")
        return
    
    question = q.TEST_1[question_num]
    selected_answer = int(callback.data)
    
    if selected_answer == question['answer']:
        user_data[user_id]['score'] += 1
        await callback.answer("Правильно!")
    else:
        correct_answer = question['options'][question['answer']]
        await callback.answer(f"Неправильно! Верный ответ: {correct_answer}")
    
    # Переходим к следующему вопросу
    user_data[user_id]['current_question'] += 1
    
    # Удаляем клавиатуру текущего сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Задаем следующий вопрос
    await ask_question(callback.message, user_id)
