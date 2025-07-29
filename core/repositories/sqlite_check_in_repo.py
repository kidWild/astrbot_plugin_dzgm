import sqlite3
from datetime import datetime, date
from typing import List
from ..database.connection import get_db_connection
from ..domain.models import CheckInRecord
from .interfaces import CheckInRepository


class SqliteCheckInRepository(CheckInRepository):
    """签到仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def create_record(self, record: CheckInRecord) -> None:
        """创建签到记录"""
        conn = get_db_connection(self.db_path)
        try:
            check_in_date = record.check_in_date
            if isinstance(check_in_date, datetime):
                check_in_date = check_in_date.date()
            
            conn.execute('''
                INSERT OR REPLACE INTO check_in_records (
                    user_id, check_in_date, coins_earned, consecutive_days, bonus_coins
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                record.user_id,
                check_in_date,
                record.coins_earned,
                record.consecutive_days,
                record.bonus_coins
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_user_check_ins(self, user_id: str, limit: int = 30) -> List[CheckInRecord]:
        """获取用户签到记录"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('''
                SELECT * FROM check_in_records 
                WHERE user_id = ?
                ORDER BY check_in_date DESC
                LIMIT ?
            ''', (user_id, limit))
            return [self._row_to_check_in_record(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_total_check_ins(self, user_id: str) -> int:
        """获取用户总签到次数"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                'SELECT COUNT(*) as count FROM check_in_records WHERE user_id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            return row['count'] if row else 0
        finally:
            conn.close()
    
    def _row_to_check_in_record(self, row) -> CheckInRecord:
        """将数据库行转换为CheckInRecord对象"""
        check_in_date = row['check_in_date']
        if isinstance(check_in_date, str):
            check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
        elif isinstance(check_in_date, datetime):
            check_in_date = check_in_date.date()
        
        return CheckInRecord(
            user_id=row['user_id'],
            check_in_date=check_in_date,
            coins_earned=row['coins_earned'],
            consecutive_days=row['consecutive_days'],
            bonus_coins=row['bonus_coins']
        )
