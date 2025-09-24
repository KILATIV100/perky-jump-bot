import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import sqlite3
from threading import Lock, Thread
import time

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфігурація
BOT_TOKEN = "8352289810:AAGP6zB_zMd9UMra1vxc-fgMv2m-hr8piG4"
WEBAPP_URL = "https://perky-jump-bot-production.up.railway.app"
PORT = int(os.environ.get('PORT', 8000))

# Flask додаток
app = Flask(__name__)
db_lock = Lock()

# Глобальна змінна для Telegram Application
telegram_app = None

# Ініціалізація бази даних
def init_db():
    with sqlite3.connect('perky_game.db') as conn:
        cursor = conn.cursor()
        
        # Таблиця користувачів
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                coins INTEGER DEFAULT 0,
                total_coffee INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                best_height INTEGER DEFAULT 0,
                selected_skin TEXT DEFAULT 'classic',
                selected_effect TEXT DEFAULT 'stars',
                owned_skins TEXT DEFAULT '["classic"]',
                owned_effects TEXT DEFAULT '["stars"]',
                upgrades TEXT DEFAULT '{}',
                settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблиця ігрових сесій
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                mode TEXT,
                height INTEGER,
                coffee_collected INTEGER,
                max_combo INTEGER,
                score INTEGER,
                time_played INTEGER,
                coins_earned INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблиця досягнень
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                achievement_id TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, achievement_id)
            )
        ''')
        
        # Таблиця лідерів
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                best_height INTEGER DEFAULT 0,
                total_coffee INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        logger.info("База даних ініціалізована")

# Ініціалізація бази даних при запуску
init_db()

# Функції роботи з базою даних
def get_user_stats(user_id):
    with db_lock:
        with sqlite3.connect('perky_game.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT coins, total_coffee, games_played, best_height, 
                       selected_skin, selected_effect, owned_skins, owned_effects,
                       upgrades, settings
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'coins': result[0],
                    'total_coffee': result[1],
                    'games_played': result[2],
                    'best_height': result[3],
                    'selected_skin': result[4],
                    'selected_effect': result[5],
                    'owned_skins': result[6],
                    'owned_effects': result[7],
                    'upgrades': result[8],
                    'settings': result[9]
                }
            return None

def save_user_info(user_data):
    with db_lock:
        with sqlite3.connect('perky_game.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, language_code, last_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_data['user_id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('language_code')
            ))
            conn.commit()

def save_game_session(session_data):
    with db_lock:
        with sqlite3.connect('perky_game.db') as conn:
            cursor = conn.cursor()
            
            # Збереження сесії
            cursor.execute('''
                INSERT INTO game_sessions 
                (user_id, mode, height, coffee_collected, max_combo, score, time_played, coins_earned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_data['user_id'],
                session_data['mode'],
                session_data['height'],
                session_data['coffee_collected'],
                session_data['max_combo'],
                session_data['score'],
                session_data['time_played'],
                session_data['coins_earned']
            ))
            
            # Оновлення статистики користувача
            cursor.execute('''
                UPDATE users SET 
                    total_coffee = total_coffee + ?,
                    games_played = games_played + 1,
                    best_height = MAX(best_height, ?),
                    coins = coins + ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                session_data['coffee_collected'],
                session_data['height'],
                session_data['coins_earned'],
                session_data['user_id']
            ))
            
            # Оновлення таблиці лідерів
            cursor.execute('''
                INSERT OR REPLACE INTO leaderboard 
                (user_id, username, first_name, best_height, total_coffee, total_score, last_updated)
                SELECT user_id, username, first_name, best_height, total_coffee, 
                       (best_height + total_coffee), CURRENT_TIMESTAMP
                FROM users WHERE user_id = ?
            ''', (session_data['user_id'],))
            
            conn.commit()

def save_user_progress(progress_data):
    with db_lock:
        with sqlite3.connect('perky_game.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET 
                    coins = ?,
                    selected_skin = ?,
                    selected_effect = ?,
                    owned_skins = ?,
                    owned_effects = ?,
                    upgrades = ?,
                    settings = ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                progress_data['coins'],
                progress_data['selected_skin'],
                progress_data['selected_effect'],
                progress_data['owned_skins'],
                progress_data['owned_effects'],
                progress_data['upgrades'],
                progress_data['settings'],
                progress_data['user_id']
            ))
            conn.commit()

def get_leaderboard(limit=10):
    with db_lock:
        with sqlite3.connect('perky_game.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, first_name, best_height, total_coffee, total_score
                FROM leaderboard 
                ORDER BY total_score DESC, best_height DESC
                LIMIT ?
            ''', (limit,))
            
            return cursor.fetchall()

def unlock_achievement(user_id, achievement_id):
    with db_lock:
        with sqlite3.connect('perky_game.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO achievements (user_id, achievement_id)
                    VALUES (?, ?)
                ''', (user_id, achievement_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Досягнення вже розблоковано

# Telegram Bot команди
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Збереження інформації про користувача
    user_data = {
        'user_id': str(user.id),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code
    }
    save_user_info(user_data)
    
    # Створення клавіатури з WebApp
    keyboard = [
        [InlineKeyboardButton("🎮 Грати", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🏆 Лідери", callback_data="leaderboard")],
        [InlineKeyboardButton("ℹ️ Допомога", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🤖☕ Вітаю в Perky Coffee Jump!

Привіт, {user.first_name}! 👋

🎯 Це захоплююча гра-стрибалка, де ти:
• Стрибаєш по платформах
• Збираєш зерна кави ☕
• Досягаєш нових висот 📏
• Розблоковуєш скіни та ефекти 🎨
• Змагаєшся з друзями 🏆

🎮 Натисни "Грати" щоб почати!
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎮 Відкрити гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🎮 Натисни кнопку щоб відкрити гру:", reply_markup=reply_markup)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    stats = get_user_stats(user_id)
    
    if stats:
        stats_text = f"""
📊 Твоя статистика:

🪙 Монети: {stats['coins']}
☕ Всього кави: {stats['total_coffee']}
🎮 Ігор зіграно: {stats['games_played']}
📏 Найкраща висота: {stats['best_height']}м

🎨 Поточний скін: {stats['selected_skin']}
✨ Поточний ефект: {stats['selected_effect']}
        """
    else:
        stats_text = "📊 Статистика недоступна. Спочатку зіграй в гру!"
    
    await update.message.reply_text(stats_text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        user_id = str(query.from_user.id)
        stats = get_user_stats(user_id)
        
        if stats:
            stats_text = f"""
📊 Твоя статистика:

🪙 Монети: {stats['coins']}
☕ Всього кави: {stats['total_coffee']}
🎮 Ігор зіграно: {stats['games_played']}
📏 Найкраща висота: {stats['best_height']}м
            """
        else:
            stats_text = "📊 Статистика недоступна. Спочатку зіграй в гру!"
        
        await query.edit_message_text(stats_text)
    
    elif query.data == "leaderboard":
        leaders = get_leaderboard(10)
        
        if leaders:
            leaderboard_text = "🏆 Таблиця лідерів:\n\n"
            for i, (username, first_name, height, coffee, score) in enumerate(leaders):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                name = first_name or username or "Гравець"
                leaderboard_text += f"{medal} {name}\n📏 {height}м | ☕ {coffee} | 🏆 {score}\n\n"
        else:
            leaderboard_text = "🏆 Таблиця лідерів порожня. Будь першим!"
        
        await query.edit_message_text(leaderboard_text)
    
    elif query.data == "help":
        help_text = """
ℹ️ Допомога по грі:

🎮 Як грати:
• Використовуй кнопки ← → для руху
• Автоматично стрибаєш при приземленні
• Збирай зерна кави ☕ для очок
• Досягай нових висот 📏

🎯 Режими гри:
• Класичний - звичайна гра
• На час - 60 секунд
• Нічний - з перешкодами
• Екстремальний - для професіоналів

🛍️ Магазин:
• Купуй скіни за монети 🪙
• Розблоковуй ефекти ✨
• Прокачуй здібності ⚡

🏆 Досягнення:
• Виконуй завдання
• Отримуй нагороди
• Змагайся з друзями
        """
        await query.edit_message_text(help_text)

# Flask маршрути
@app.route('/')
def index():
    return "🤖☕ Perky Coffee Jump Bot працює!"

@app.route('/game')
def game():
    # Тут буде HTML код гри (створимо в наступному файлі)
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Perky Coffee Jump</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
    </head>
    <body>
        <h1>🎮 Perky Coffee Jump</h1>
        <p>Гра завантажується...</p>
        <script>
            // Тимчасовий код - замінимо на повну гру
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
            }
        </script>
    </body>
    </html>
    """)

# API endpoints
@app.route('/api/user_info', methods=['POST'])
def save_user_info_api():
    try:
        user_data = request.json
        save_user_info(user_data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Помилка збереження користувача: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user_stats/<user_id>')
def get_user_stats_api(user_id):
    try:
        stats = get_user_stats(user_id)
        if stats:
            return jsonify(stats)
        else:
            return jsonify({'coins': 0, 'total_coffee': 0, 'games_played': 0, 'best_height': 0})
    except Exception as e:
        logger.error(f"Помилка отримання статистики: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_game', methods=['POST'])
def save_game_api():
    try:
        session_data = request.json
        save_game_session(session_data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Помилка збереження гри: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_progress', methods=['POST'])
def save_progress_api():
    try:
        progress_data = request.json
        save_user_progress(progress_data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Помилка збереження прогресу: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/leaderboard')
def leaderboard_api():
    try:
        leaders = get_leaderboard(10)
        result = []
        for username, first_name, height, coffee, score in leaders:
            result.append({
                'username': username,
                'first_name': first_name,
                'best_height': height,
                'total_coffee': coffee,
                'total_score': score
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Помилка отримання лідерів: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/unlock_achievement', methods=['POST'])
def unlock_achievement_api():
    try:
        data = request.json
        success = unlock_achievement(data['user_id'], data['achievement_id'])
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Помилка розблокування досягнення: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Webhook для Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, telegram_app.bot)
        
        # Обробка оновлення в окремому потоці
        def process_update():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(telegram_app.process_update(update))
            loop.close()
        
        thread = Thread(target=process_update)
        thread.start()
        
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"Помилка webhook: {e}")
        return jsonify({'ok': False}), 500

# Налаштування webhook
async def setup_webhook():
    webhook_url = f"{WEBAPP_URL}/webhook"
    await telegram_app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook налаштовано: {webhook_url}")

# Ініціалізація Telegram бота
def init_telegram_bot():
    global telegram_app
    
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    
    # Додавання обробників
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("game", game_command))
    telegram_app.add_handler(CommandHandler("stats", stats_command))
    telegram_app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Telegram бот ініціалізовано")

# Запуск сервера
def run_server():
    init_telegram_bot()
    
    # Налаштування webhook в окремому потоці
    def setup_webhook_thread():
        time.sleep(2)  # Чекаємо запуску сервера
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_webhook())
        loop.close()
    
    webhook_thread = Thread(target=setup_webhook_thread)
    webhook_thread.start()
    
    # Запуск Flask сервера
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == '__main__':
    logger.info("🚀 Запуск Perky Coffee Jump Bot...")
    run_server()
