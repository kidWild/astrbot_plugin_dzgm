import sqlite3
from datetime import datetime
from typing import List
from ..database.connection import get_db_connection
from ..domain.models import UserAchievement
from .interfaces import UserAchievementRepository


class SqliteUserAchievementRepository(UserAchievementRepository):
    """用户成就仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        """获取用户所有成就"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('''
                SELECT * FROM user_achievements 
                WHERE user_id = ?
                ORDER BY achieved_at DESC
            ''', (user_id,))
            return [self._row_to_user_achievement(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def has_achievement(self, user_id: str, achievement_id: str) -> bool:
        """检查用户是否拥有某成就"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                'SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?',
                (user_id, achievement_id)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def award_achievement(self, user_achievement: UserAchievement) -> None:
        """颁发成就"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute('''
                INSERT OR IGNORE INTO user_achievements (
                    user_id, achievement_id, achieved_at, notified
                ) VALUES (?, ?, ?, ?)
            ''', (
                user_achievement.user_id,
                user_achievement.achievement_id,
                user_achievement.achieved_at,
                user_achievement.notified
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_unnotified_achievements(self, user_id: str) -> List[UserAchievement]:
        """获取未通知的成就"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('''
                SELECT * FROM user_achievements 
                WHERE user_id = ? AND notified = FALSE
                ORDER BY achieved_at ASC
            ''', (user_id,))
            return [self._row_to_user_achievement(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def mark_as_notified(self, user_id: str, achievement_id: str) -> None:
        """标记成就为已通知"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute('''
                UPDATE user_achievements 
                SET notified = TRUE 
                WHERE user_id = ? AND achievement_id = ?
            ''', (user_id, achievement_id))
            conn.commit()
        finally:
            conn.close()
    
    def _row_to_user_achievement(self, row) -> UserAchievement:
        """将数据库行转换为UserAchievement对象"""
        return UserAchievement(
            user_id=row['user_id'],
            achievement_id=row['achievement_id'],
            achieved_at=datetime.fromisoformat(row['achieved_at']),
            notified=bool(row['notified'])
        )
