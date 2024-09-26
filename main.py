import telebot
from telebot import types
import psycopg2
import ssl
import os
from dotenv import load_dotenv

load_dotenv(override=True)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot_username = "x_turbo_bot"

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context = ssl.create_default_context(cafile='/home/fiornrrn/.postgresql/root.crt')

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_SSL_MODE = os.getenv('DB_SSL_MODE', 'verify-full')
DB_SSL_ROOT_CERT = os.getenv('DB_SSL_ROOT_CERT')
DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSL_MODE}&sslrootcert={DB_SSL_ROOT_CERT}"

try:
    conn = psycopg2.connect(DB_CONNECTION_STRING, sslmode='verify-full', sslrootcert='/home/fiornrrn/.postgresql/root.crt')
    conn.autocommit = True
    print("Connected to the database")
except Exception as e:
    print(f"Error connecting to the database: {e}")
    exit(1)

def create_table():
    with conn.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                start_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

create_table()

@bot.message_handler(commands=['add_source'])
def add_source(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    cancel_button = types.KeyboardButton('Отменить')
    markup.add(cancel_button)
    bot.send_message(message.chat.id, "Введите название источника:", reply_markup=markup)
    bot.register_next_step_handler(message, process_source_name)

def process_source_name(message):
    source_name = message.text.strip()

    remove_markup = types.ReplyKeyboardRemove()

    if source_name == 'Отменить':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=remove_markup)
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO sources (name, url)
                VALUES (%s, %s)
                RETURNING id
            ''', (source_name, ''))
            source_id = cursor.fetchone()

            if source_id is None:
                bot.send_message(message.chat.id, "Ошибка при добавлении источника.", reply_markup=remove_markup)
                return

            source_id = source_id[0]

            link = f"https://t.me/{bot_username}?start={source_id}"

            cursor.execute('''
                UPDATE sources SET url = %s WHERE id = %s
            ''', (link, source_id))

        bot.send_message(
            message.chat.id,
            f"Ваш источник добавлен. Вот ваша ссылка:\n{link}",
            reply_markup=remove_markup
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}", reply_markup=remove_markup)

@bot.message_handler(commands=['sources'])
def list_sources(message):
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, name, url FROM sources')
            sources = cursor.fetchall()

            if not sources:
                bot.send_message(message.chat.id, "Нет доступных источников.")
                return

            response = "Список источников:\nID - Название - Ссылка\n"
            for source_id, name, url in sources:
                response += f"{source_id} - {name} - {url}\n"

            bot.send_message(message.chat.id, response)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}")

@bot.message_handler(commands=['delete_source'])
def delete_source(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    cancel_button = types.KeyboardButton('Отменить')
    markup.add(cancel_button)
    bot.send_message(message.chat.id, "Введите ID источника для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, process_delete_source)

def process_delete_source(message):
    source_id = message.text.strip()

    remove_markup = types.ReplyKeyboardRemove()

    if source_id == 'Отменить':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=remove_markup)
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM sources WHERE id = %s RETURNING id', (source_id,))
            deleted_id = cursor.fetchone()

            if deleted_id is None:
                bot.send_message(message.chat.id, "Источник с указанным ID не найден.", reply_markup=remove_markup)
                return

        bot.send_message(message.chat.id, f"Источник с ID {source_id} успешно удален.", reply_markup=remove_markup)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}", reply_markup=remove_markup)

print("Bot is running...")
bot.polling()
