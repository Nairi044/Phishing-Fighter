import logging
import config
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from aiogram import Bot, Dispatcher, types
from aiogram.utils.exceptions import BadRequest
import time

# Set up logging
logging.basicConfig(level=logging.INFO)

# Create bot instance
bot = Bot(token=config.TOKEN)

# Create dispatcher instance
dp = Dispatcher(bot)

# Set up database connection
engine = create_engine('sqlite:///chatbot.db')
Session = sessionmaker(bind=engine)
Base = declarative_base()
MESSAGE = None


class UserLink(Base):
    __tablename__ = 'user_links'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    link = Column(String, nullable=False)


Base.metadata.create_all(engine)

async def send_message_to_admins(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Approve", callback_data="approve"))
    keyboard.add(types.InlineKeyboardButton("Reject", callback_data="reject"))
    for user_id in config.ADMIN_IDS:
        try:
            await message.forward(user_id)
            await bot.send_message(chat_id=user_id, text="Հաստատե՞լ նամակը։", reply_markup=keyboard)
        except BadRequest:
            pass

@dp.callback_query_handler(lambda c: c.data == 'approve')
async def approve_link(callback_query: types.CallbackQuery):
    global MESSAGE
    user_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    chat_id = callback_query.message.chat.id
    await bot.send_message(chat_id, f"Link approved by user with ID {user_id}. Message ID: {message_id}")
    new_message = f"Message from: {MESSAGE.from_user.full_name}" + \
        (f", @{MESSAGE.from_user.username}" if MESSAGE.from_user.username else "") + \
        f"\n\n{MESSAGE.text}"
    await bot.send_message(MESSAGE.chat.id, new_message)
    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
    await callback_query.answer("Link Approved")

def check_for_link_in_text(message):
    if message.text and message.entities:
        for entity in message.entities:
            if entity.type == "url":
                return True
    return False

def check_for_link_in_inline_buttons(message):
    if message and message.reply_markup and message.reply_markup.inline_keyboard:
        for markup in message.reply_markup.inline_keyboard:
            if markup[0].url != "":
                return True
    return False


def check_for_link_in_image(message):
    if message.photo:
        if message.caption and message.caption_entities:
            for entity in message.caption_entities:
                if entity.type == "url":
                    return True

        if message.reply_markup:
            for keys in message.reply_markup:
                for key in keys[1]:
                    for k in key:
                        if k["url"] != "":
                            return True
    return False

def check_for_all(message):
    return (check_for_link_in_image(message)
            or check_for_link_in_text(message)
            or check_for_link_in_inline_buttons(message))


@dp.message_handler()
async def get_messages(message):
    global MESSAGE
    if check_for_all(message):
        MESSAGE = message
        await message.reply("Ձեր յղումը ուղարկուած է ստուգման, Խնդրում ենք սպասել!")
        await send_message_to_admins(message)
        await message.delete()

@dp.message_handler(content_types=types.ContentTypes.PHOTO | types.ContentTypes.TEXT)
async def handle_image_with_link(message: types.Message):
    if check_for_all(message):
        MESSAGE = message
        await message.reply("Ձեր յղումը ուղարկուած է ստուգման, Խնդրում ենք սպասել!")
        await send_message_to_admins(message)
        await message.delete()

if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)

