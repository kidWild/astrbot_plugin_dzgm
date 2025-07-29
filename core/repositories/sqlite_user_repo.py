import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from ..database.connection import get_db_connection
from ..domain.models import User, LeaderboardEntry
from .interfaces import UserRepository


class SqliteUserRepository(UserRepository):
    """用户仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                'SELECT * FROM users WHERE user_id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_user(row)
            return None
        finally:
            conn.close()
    
    def save(self, user: User) -> None:
        """保存用户（更新）"""
        conn = get_db_connection(self.db_path)
        try:
            user.updated_at = datetime.now()
            conn.execute('''
                UPDATE users SET
                    username = ?, coins = ?, total_earned = ?, total_spent = ?,
                    check_in_count = ?, last_check_in = ?, total_check_ins = ?,
                    level = ?, experience = ?, title = ?, updated_at = ?
                WHERE user_id = ?
            ''', (
                user.username, user.coins, user.total_earned, user.total_spent,
                user.check_in_count, user.last_check_in, user.total_check_ins,
                user.level, user.experience, user.title, user.updated_at,
                user.user_id
            ))
            conn.commit()
        finally:
            conn.close()
    
    def create(self, user: User) -> None:
        """创建新用户"""
        conn = get_db_connection(self.db_path)
        try:
            if not user.created_at:
                user.created_at = datetime.now()
                user.updated_at = datetime.now()
            
            conn.execute('''
                INSERT INTO users (
                    user_id, username, coins, total_earned, total_spent,
                    check_in_count, last_check_in, total_check_ins,
                    level, experience, title, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.user_id, user.username, user.coins, user.total_earned, user.total_spent,
                user.check_in_count, user.last_check_in, user.total_check_ins,
                user.level, user.experience, user.title, user.created_at, user.updated_at
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_leaderboard(self, limit: int = 10, offset: int = 0) -> List[LeaderboardEntry]:
        """获取排行榜"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('''
                SELECT user_id, username, coins, title,
                       ROW_NUMBER() OVER (ORDER BY coins DESC) as rank
                FROM users
                ORDER BY coins DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            entries = []
            for row in cursor.fetchall():
                entries.append(LeaderboardEntry(
                    rank=row['rank'],
                    user_id=row['user_id'],
                    username=row['username'],
                    score=row['coins'],
                    title=row['title']
                ))
            return entries
        finally:
            conn.close()
    
    def get_user_rank(self, user_id: str) -> Optional[int]:
        """获取用户排名"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('''
                WITH ranked_users AS (
                    SELECT user_id, ROW_NUMBER() OVER (ORDER BY coins DESC) as rank
                    FROM users
                )
                SELECT rank FROM ranked_users WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            return row['rank'] if row else None
        finally:
            conn.close()
    
    def _row_to_user(self, row) -> User:
        """将数据库行转换为User对象"""
        return User(
            user_id=row['user_id'],
            username=row['username'],
            coins=row['coins'],
            total_earned=row['total_earned'],
            total_spent=row['total_spent'],
            check_in_count=row['check_in_count'],
            last_check_in=datetime.fromisoformat(row['last_check_in']) if row['last_check_in'] else None,
            total_check_ins=row['total_check_ins'],
            level=row['level'],
            experience=row['experience'],
            title=row['title'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
