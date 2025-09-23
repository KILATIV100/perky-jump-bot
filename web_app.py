import os
import sqlite3
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from flask import Flask, request, jsonify

# Завантажуємо змінні середовища з файлу .env, якщо він існує
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Модуль python-dotenv не знайдено. Будуть використані змінні середовища системи.")

# Змінні середовища з вашого запиту
BOT_TOKEN = os.getenv("BOT_TOKEN", "7510044716:AAEsQS5DmtDcdR78hTOfHyNnb8Nou9IHO1Q")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://perky-jump-bot-production.up.railway.app")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBAPP_URL}/webhook")

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

# Команда /start - вітає користувача і показує меню
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[
        InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=WEBAPP_URL)),
        InlineKeyboardButton("🆘 Допомога", callback_data='help')
    ], [
        InlineKeyboardButton("📊 Статистика", callback_data='stats'),
        InlineKeyboardButton("🛒 Магазин", callback_data='shop')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Привіт! Обирай, що робити:', reply_markup=reply_markup)

    # Зберігаємо користувача в БД, якщо його там ще немає
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
    # Telegram API дозволяє нам отримати web_app_data, але для збереження
    # статистики ми використовуємо Flask, щоб обробляти POST-запити від гри.
    # Цей обробник потрібен для інших видів даних, які можуть надходити.
    pass

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

        conn = sqliteite3.connect('game_stats.db')
        cursor = conn.cursor()
        
        # Оновлюємо статистику користувача, зберігаючи максимальну висоту
        # та додаючи зібрані зерна
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

# ---- Запуск бота та веб-сервера ----
if __name__ == '__main__':
    # Ініціалізуємо БД
    init_db()

    # Створюємо оновлювач бота
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Додаємо обробники команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("stats", stats_command))

    # Запускаємо веб-сервер Flask
    # На Railway, він автоматично буде працювати на потрібному порті
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

    # Запускаємо бота
    # Використовуємо `updater.start_webhook` для розгортання на Railway
    updater.start_webhook(listen="0.0.0.0",
                          port=port,
                          url_path=f"/{BOT_TOKEN}")
    updater.bot.set_webhook(f"{WEBAPP_URL}/{BOT_TOKEN}")
    updater.idle()