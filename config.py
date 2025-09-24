import os
from typing import Dict, Any

class Config:
    """Базова конфігурація"""
    
    # Telegram Bot
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'perky_game.db')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Railway
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')
    
    # Game Settings
    GAME_SETTINGS = {
        'max_height': 10000,
        'max_coffee_per_game': 200,
        'coin_multiplier': 0.1,
        'daily_challenge_refresh_hour': 0,
        'leaderboard_size': 100
    }
    
    # Achievement Settings
    ACHIEVEMENT_SETTINGS = {
        'coffee_milestones': [10, 25, 50, 100, 200],
        'height_milestones': [50, 100, 200, 500, 1000],
        'score_milestones': [500, 1000, 2500, 5000, 10000],
        'games_milestones': [1, 5, 10, 25, 50, 100]
    }
    
    # Shop Items
    SHOP_ITEMS = {
        'skins': {
            'robot': {'price': 100, 'name': 'Робот'},
            'ninja': {'price': 150, 'name': 'Ніндзя'},
            'astronaut': {'price': 200, 'name': 'Астронавт'},
            'pirate': {'price': 250, 'name': 'Пірат'},
            'wizard': {'price': 300, 'name': 'Чарівник'}
        },
        'trails': {
            'fire': {'price': 50, 'name': 'Вогняний слід'},
            'ice': {'price': 75, 'name': 'Льодяний слід'},
            'rainbow': {'price': 100, 'name': 'Райдужний слід'},
            'stars': {'price': 125, 'name': 'Зоряний слід'},
            'hearts': {'price': 150, 'name': 'Сердечка'}
        },
        'upgrades': {
            'double_jump': {'price': 200, 'name': 'Подвійний стрибок'},
            'shield': {'price': 300, 'name': 'Щит'},
            'magnet': {'price': 250, 'name': 'Магніт'},
            'turbo': {'price': 350, 'name': 'Турбо'}
        }
    }
    
    # API Rate Limiting
    RATE_LIMIT_SETTINGS = {
        'requests_per_minute': 60,
        'requests_per_hour': 1000,
        'burst_limit': 10
    }
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def get_database_url(cls) -> str:
        """Отримати URL бази даних"""
        return cls.DATABASE_URL
    
    @classmethod
    def is_production(cls) -> bool:
        """Перевірити чи це продакшн середовище"""
        return os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    
    @classmethod
    def get_cors_origins(cls) -> list:
        """Отримати дозволені CORS origins"""
        if cls.is_production():
            return [
                'https://web.telegram.org',
                'https://k.telegram.org',
                cls.WEBHOOK_URL
            ]
        return ['*']

class DevelopmentConfig(Config):
    """Конфігурація для розробки"""
    DEBUG = True
    DATABASE_URL = 'perky_game_dev.db'

class ProductionConfig(Config):
    """Конфігурація для продакшну"""
    DEBUG = False
    
    @classmethod
    def get_database_url(cls) -> str:
        # Для Railway використовуємо PostgreSQL якщо доступний
        postgres_url = os.getenv('DATABASE_URL')
        if postgres_url and postgres_url.startswith('postgres://'):
            # Railway надає postgres://, але SQLAlchemy потребує postgresql://
            return postgres_url.replace('postgres://', 'postgresql://', 1)
        return super().get_database_url()

class TestingConfig(Config):
    """Конфігурація для тестування"""
    TESTING = True
    DATABASE_URL = ':memory:'  # In-memory SQLite для тестів

# Вибір конфігурації на основі середовища
def get_config() -> Config:
    env = os.getenv('FLASK_ENV', 'development')
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()

# Експорт поточної конфігурації
config = get_config()
