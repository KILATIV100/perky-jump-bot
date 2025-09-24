from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

@dataclass
class User:
    id: int
    telegram_id: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    coins: int = 0
    total_coffee: int = 0
    games_played: int = 0
    best_height: int = 0
    best_coffee: int = 0
    total_score: int = 0
    created_at: datetime = None
    last_active: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'coins': self.coins,
            'total_coffee': self.total_coffee,
            'games_played': self.games_played,
            'best_height': self.best_height,
            'best_coffee': self.best_coffee,
            'total_score': self.total_score
        }

@dataclass
class GameSession:
    id: Optional[int]
    user_id: int
    mode: str
    height: int = 0
    coffee_collected: int = 0
    max_combo: int = 0
    score: int = 0
    time_played: int = 0
    coins_earned: int = 0
    created_at: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mode': self.mode,
            'height': self.height,
            'coffee_collected': self.coffee_collected,
            'max_combo': self.max_combo,
            'score': self.score,
            'time_played': self.time_played,
            'coins_earned': self.coins_earned,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class Achievement:
    id: Optional[int]
    user_id: int
    achievement_type: str
    achievement_data: Optional[str] = None
    unlocked_at: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'achievement_type': self.achievement_type,
            'achievement_data': json.loads(self.achievement_data) if self.achievement_data else None,
            'unlocked_at': self.unlocked_at.isoformat() if self.unlocked_at else None
        }

@dataclass
class DailyChallenge:
    id: Optional[int]
    user_id: int
    challenge_type: str
    target_value: int
    current_progress: int = 0
    completed: bool = False
    reward_coins: int = 0
    date_assigned: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'challenge_type': self.challenge_type,
            'target_value': self.target_value,
            'current_progress': self.current_progress,
            'completed': self.completed,
            'reward_coins': self.reward_coins,
            'date_assigned': self.date_assigned.isoformat() if self.date_assigned else None
        }

@dataclass
class Friendship:
    id: Optional[int]
    user_id: int
    friend_id: int
    status: str = 'pending'
    created_at: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'friend_id': self.friend_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Константи для досягнень
ACHIEVEMENTS = {
    'first_game': {
        'name': 'Перша гра',
        'description': 'Зіграв свою першу гру',
        'reward_coins': 10
    },
    'coffee_collector_10': {
        'name': 'Збирач кави',
        'description': 'Зібрав 10 зерен кави за гру',
        'reward_coins': 25
    },
    'coffee_collector_50': {
        'name': 'Кавовий експерт',
        'description': 'Зібрав 50 зерен кави за гру',
        'reward_coins': 50
    },
    'height_master_50': {
        'name': 'Високий стрибун',
        'description': 'Досяг висоти 50м',
        'reward_coins': 30
    },
    'height_master_100': {
        'name': 'Майстер висоти',
        'description': 'Досяг висоти 100м',
        'reward_coins': 75
    },
    'score_master_500': {
        'name': 'Майстер очок',
        'description': 'Набрав 500 очок за гру',
        'reward_coins': 40
    },
    'games_played_10': {
        'name': 'Постійний гравець',
        'description': 'Зіграв 10 ігор',
        'reward_coins': 60
    },
    'total_coffee_100': {
        'name': 'Кавовий колекціонер',
        'description': 'Зібрав 100 зерен кави загалом',
        'reward_coins': 80
    }
}

# Константи для щоденних завдань
DAILY_CHALLENGES = {
    'collect_coffee': {
        'name': 'Збери каву',
        'description': 'Збери {target} зерен кави',
        'reward_coins': 20
    },
    'reach_height': {
        'name': 'Досягни висоти',
        'description': 'Досягни висоти {target}м',
        'reward_coins': 25
    },
    'play_games': {
        'name': 'Зіграй ігри',
        'description': 'Зіграй {target} ігор',
        'reward_coins': 15
    },
    'score_points': {
        'name': 'Набери очки',
        'description': 'Набери {target} очок за гру',
        'reward_coins': 30
    }
}
