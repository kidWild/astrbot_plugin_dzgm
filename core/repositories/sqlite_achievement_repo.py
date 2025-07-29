import sqlite3
from datetime import datetime
from typing import List, Optional
from ..database.connection import get_db_connection
from ..domain.models import Achievement
from .interfaces import AchievementRepository


class SqliteAchievementRepository(AchievementRepository):
    """成就仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_all(self) -> List[Achievement]:
        """获取所有成就"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('SELECT * FROM achievements ORDER BY category, id')
            return [self._row_to_achievement(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_by_id(self, achievement_id: str) -> Optional[Achievement]:
        """根据ID获取成就"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                'SELECT * FROM achievements WHERE id = ?',
                (achievement_id,)
            )
            row = cursor.fetchone()
            return self._row_to_achievement(row) if row else None
        finally:
            conn.close()
    
    def get_by_category(self, category: str) -> List[Achievement]:
        """根据分类获取成就"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                'SELECT * FROM achievements WHERE category = ? ORDER BY id',
                (category,)
            )
            return [self._row_to_achievement(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def create(self, achievement: Achievement) -> None:
        """创建成就"""
        conn = get_db_connection(self.db_path)
        try:
            if not achievement.created_at:
                achievement.created_at = datetime.now()
            
            conn.execute('''
                INSERT OR REPLACE INTO achievements (
                    id, name, description, category, condition_type, condition_value,
                    reward_coins, reward_title, icon, is_hidden, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                achievement.id, achievement.name, achievement.description,
                achievement.category, achievement.condition_type, achievement.condition_value,
                achievement.reward_coins, achievement.reward_title, achievement.icon,
                achievement.is_hidden, achievement.created_at
            ))
            conn.commit()
        finally:
            conn.close()
    
    def _row_to_achievement(self, row) -> Achievement:
        """将数据库行转换为Achievement对象"""
        return Achievement(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            category=row['category'],
            condition_type=row['condition_type'],
            condition_value=row['condition_value'],
            reward_coins=row['reward_coins'],
            reward_title=row['reward_title'],
            icon=row['icon'],
            is_hidden=bool(row['is_hidden']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
