import os
import sqlite3
import asyncio
from flask import Flask, request, jsonify
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# ---- Функції для команд бота ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    webapp_url = os.getenv("WEBAPP_URL")
    if not webapp_url:
        await update.message.reply_text('Помилка: Не знайдено WEBAPP_URL.')
        return
    
    keyboard = [[
        InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=webapp_url)),
        InlineKeyboardButton("📊 Статистика", callback_data='stats')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Привіт! Обирай, що робити:', reply_markup=reply_markup)
    
    user_id = update.effective_user.id
    username = update.effective_user.username
    conn = sqlite3.connect('game_stats.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conn = sqlite3.connect('game_stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT max_height, collected_beans FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        max_height, collected_beans = result
        response = f"📊 *Ваша статистика:*\n" \
                   f"Максимальна висота: *{max_height} м*\n" \
                   f"Зібрано зерен: *{collected_beans}*"
    else:
        response = "Не знайдено статистики. Спробуйте зіграти першу гру!"
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass

# ---- Фабрична функція Flask ----
def create_app():
    """Створює та налаштовує застосунок Flask."""
    app = Flask(__name__)
    
    # Ініціалізуємо БД при створенні застосунку
    init_db()

    # Створюємо екземпляр Application для бота
    bot_token = os.getenv("BOT_TOKEN")
    application = Application.builder().token(bot_token).build()
    
    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    @app.route('/save_stats', methods=['POST'])
    def save_stats():
        try:
            data = request.json
            user_id = data.get('user_id')
            score = data.get('score')
            collected_beans = data.get('collected_beans')
            
            if not all([user_id, score, collected_beans]):
                return jsonify({"status": "error", "message": "Відсутні дані"}), 400
            
            conn = sqlite3.connect('game_stats.db')
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
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

    @app.route('/', methods=['POST'])
    async def webhook():
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return 'ok'

    return app

# Ініціалізуємо базу даних (залишимо тут для зручності)
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

# Додаємо цю умову для локального запуску, Gunicorn її ігнорує
if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
