import sqlite3
import os
from datetime import datetime
import json

class Database:
    def __init__(self, db_path="perky_game.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Ініціалізація бази даних з усіма таблицями"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблиця користувачів
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 0,
                total_coffee INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                best_height INTEGER DEFAULT 0,
                best_coffee INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблиця ігрових сесій
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mode TEXT NOT NULL,
                height INTEGER DEFAULT 0,
                coffee_collected INTEGER DEFAULT 0,
                max_combo INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                time_played INTEGER DEFAULT 0,
                coins_earned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблиця досягнень
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_type TEXT NOT NULL,
                achievement_data TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблиця друзів
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                friend_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (friend_id) REFERENCES users (id)
            )
        ''')
        
        # Таблиця щоденних завдань
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                challenge_type TEXT NOT NULL,
                target_value INTEGER NOT NULL,
                current_progress INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                reward_coins INTEGER DEFAULT 0,
                date_assigned DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблиця покупок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                price INTEGER NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        """Отримати або створити користувача"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name))
            conn.commit()
            
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = cursor.fetchone()
        
        conn.close()
        return user
    
    def save_game_session(self, session_data):
        """Зберегти ігрову сесію"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Отримати user_id по telegram_id
        cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (session_data['user_id'],))
        user_row = cursor.fetchone()
        
        if not user_row:
            conn.close()
            return False
        
        user_id = user_row[0]
        
        # Зберегти сесію
        cursor.execute('''
            INSERT INTO game_sessions 
            (user_id, mode, height, coffee_collected, max_combo, score, time_played, coins_earned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            session_data['mode'],
            session_data['height'],
            session_data['coffee_collected'],
            session_data['max_combo'],
            session_data['score'],
            session_data['time_played'],
            session_data['coins_earned']
        ))
        
        # Оновити статистику користувача
        cursor.execute('''
            UPDATE users SET
                coins = coins + ?,
                total_coffee = total_coffee + ?,
                games_played = games_played + 1,
                best_height = MAX(best_height, ?),
                best_coffee = MAX(best_coffee, ?),
                total_score = MAX(total_score, ?),
                last_active = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', (
            session_data['coins_earned'],
            session_data['coffee_collected'],
            session_data['height'],
            session_data['coffee_collected'],
            session_data['score'],
            session_data['user_id']
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user_stats(self, telegram_id):
        """Отримати статистику користувача"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return None
        
        # Отримати останні ігри
        cursor.execute('''
            SELECT * FROM game_sessions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user[0],))
        recent_games = cursor.fetchall()
        
        conn.close()
        
        return {
            'coins': user[5],
            'total_coffee': user[6],
            'games_played': user[7],
            'best_height': user[8],
            'best_coffee': user[9],
            'total_score': user[10],
            'recent_games': recent_games
        }
    
    def get_leaderboard(self, limit=50):
        """Отримати таблицю лідерів"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT telegram_id, username, first_name, best_height, best_coffee, total_score, games_played
            FROM users 
            ORDER BY best_height DESC, total_score DESC 
            LIMIT ?
        ''', (limit,))
        
        leaderboard = cursor.fetchall()
        conn.close()
        
        return leaderboard
