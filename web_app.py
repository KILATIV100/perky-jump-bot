import os
import sqlite3
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

# Завантажуємо змінні середовища з файлу .env, якщо він існує
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Змінні середовища
BOT_TOKEN = os.getenv("BOT_TOKEN", "8352289810:AAGP6zB_zMd9UMra1vxc-fgMv2m-hr8piG4")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://perky-jump-bot-production.up.railway.app")

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

# ---- Функції для команд бота ----

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not WEBAPP_URL:
        await update.message.reply_text('Помилка: Не знайдено WEBAPP_URL. Зверніться до адміністратора.')
        return

    keyboard = [[
        InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=WEBAPP_URL)),
        InlineKeyboardButton("🆘 Допомога", callback_data='help')
    ], [
        InlineKeyboardButton("📊 Статистика", callback_data='stats'),
        InlineKeyboardButton("🛒 Магазин", callback_data='shop')
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

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Інструкції з гри та пояснення. Наша мета - піднятися якомога вище. Збирайте кавові зерна, щоб отримати більше очок!')

# Команда /stats
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

# Обробка даних, що надходять з Web App
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Цей обробник порожній, оскільки Flask-сервер обробляє POST-запити з гри
    pass

# ---- Налаштування Flask для обробки даних ----
app = Flask(__name__)

# Створюємо екземпляр Application для бота
application = Application.builder().token(BOT_TOKEN).build()

# Додаємо обробники команд
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("stats", stats_command))
application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

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

# ---- Налаштування webhook для Flask ----
@app.route('/', methods=['POST'])
async def webhook():
    """Обробляє оновлення від Telegram, надсилаючи їх в Application бота."""
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, application.bot)
    
    # Тепер використовуємо await, оскільки process_update є асинхронним
    await application.process_update(update)
    return 'ok'

if __name__ == '__main__':
    # Ініціалізуємо БД
    init_db()

    # Встановлюємо webhook, оскільки ми запускаємо bot-частину через Flask-webhook
    async def run_bot():
        webhook_url = f"{WEBAPP_URL}/{BOT_TOKEN}"
        await application.bot.set_webhook(url=webhook_url)

    # Запускаємо веб-сервер Flask, який буде обробляти запити з гри
    # та вебхуки від Telegram.
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

