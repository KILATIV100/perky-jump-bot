import os
import sqlite3
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, filters
from flask import Flask, request, jsonify

# Завантажуємо змінні середовища з файлу .env, якщо він існує
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Модуль python-dotenv не знайдено. Будуть використані змінні середовища системи.")

# Змінні середовища з вашого запиту
BOT_TOKEN = os.getenv("BOT_TOKEN", "8352289810:AAGP6zB_zMd9UMra1vxc-fgMv2m-hr8piG4")

# Ініціалізуємо базу даних SQLite
def init_db():
    conn = sqlite3.connect('game_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            max_height INTEGER DEFAULT 0,
            collected_beans INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# ---- Налаштування Flask для обробки даних з Web App ----
app = Flask(__name__)

@app.route('/save_stats', methods=['POST'])
def save_stats():
    """Обробляє POST-запит від Web App і зберігає статистику в БД."""
    try:
        data = request.json
        user_id = data.get('user_id')
        score = data.get('score')
        collected_beans = data.get('collected_beans')

        if not user_id or score is None or collected_beans is None:
            return jsonify({"status": "error", "message": "Відсутні дані"}), 400

        conn = sqlite3.connect('game_stats.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET 
            max_height = MAX(max_height, ?), 
            collected_beans = collected_beans + ? 
            WHERE user_id = ?
        ''', (score, collected_beans, user_id))
        conn.commit()
        conn.close()

        return jsonify({"status": "ok", "message": "Статистика оновлена"}), 200

    except Exception as e:
        print(f"Помилка при обробці статистики: {e}")
        return jsonify({"status": "error", "message": "Внутрішня помилка сервера"}), 500

# ---- Налаштування бота ----
updater = Updater(BOT_TOKEN)
dispatcher = updater.dispatcher

# Команда /start - вітає користувача і показує меню
def start(update: Update, context: CallbackContext) -> None:
    # Отримуємо WEBAPP_URL з environment variables
    WEBAPP_URL = os.getenv("WEBAPP_URL", "")
    if not WEBAPP_URL:
        update.message.reply_text('Помилка: Не знайдено WEBAPP_URL. Зверніться до адміністратора.')
        return

    keyboard = [[
        InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=WEBAPP_URL)),
        InlineKeyboardButton("🆘 Допомога", callback_data='help')
    ], [
        InlineKeyboardButton("📊 Статистика", callback_data='stats'),
        InlineKeyboardButton("🛒 Магазин", callback_data='shop')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Привіт! Обирай, що робити:', reply_markup=reply_markup)

    user_id = update.effective_user.id
    username = update.effective_user.username
    conn = sqlite3.connect('game_stats.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

# Команда /help
def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Інструкції з гри та пояснення. Наша мета - піднятися якомога вище. Збирайте кавові зерна, щоб отримати більше очок!')

# Команда /stats
def stats_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    conn = sqlite3.connect('game_stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT max_height, collected_beans FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        max_height, collected_beans = result
        response = f"📊 **Ваша статистика:**\n" \
                   f"Максимальна висота: **{max_height} м**\n" \
                   f"Зібрано зерен: **{collected_beans}**"
    else:
        response = "Не знайдено статистики. Спробуйте зіграти першу гру!"
    
    update.message.reply_markdown_v2(response)

# Обробка даних, що надходять з Web App
def handle_webapp_data(update: Update, context: CallbackContext) -> None:
    pass

# Додаємо обробники команд
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("stats", stats_command))
dispatcher.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

# ---- Налаштування webhook для Flask ----
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    """Обробляє оновлення від Telegram, надсилаючи їх у dispatcher бота."""
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dispatcher.process_update(update)
    return 'ok'

if __name__ == '__main__':
    # Ініціалізуємо БД
    init_db()

    # Запускаємо веб-сервер Flask
    # Gunicorn на Railway запускає `app`
    # Цей блок необхідний лише для локального тестування
    app.run(host='0.0.0.0', port=8000)
