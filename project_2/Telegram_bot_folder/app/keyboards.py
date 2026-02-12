from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder



main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Приступить к тесту', callback_data='test')]
])

