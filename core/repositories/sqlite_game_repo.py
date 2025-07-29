import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from ..database.connection import get_db_connection
from ..domain.models import GameRecord, GameRoom
from .interfaces import GameRepository


class SqliteGameRepository(GameRepository):
    """游戏记录和房间仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def create_record(self, record: GameRecord) -> None:
        """创建游戏记录"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute('''
                INSERT INTO game_records (
                    user_id, game_type, coins_bet, coins_won, result, details, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.user_id,
                record.game_type,
                record.coins_bet,
                record.coins_won,
                record.result,
                json.dumps(record.details) if record.details else None,
                record.created_at or datetime.now()
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_user_game_records(self, user_id: str, game_type: Optional[str] = None, limit: int = 50) -> List[GameRecord]:
        """获取用户游戏记录"""
        conn = get_db_connection(self.db_path)
        try:
            if game_type:
                cursor = conn.execute('''
                    SELECT * FROM game_records 
                    WHERE user_id = ? AND game_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (user_id, game_type, limit))
            else:
                cursor = conn.execute('''
                    SELECT * FROM game_records 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (user_id, limit))
            
            return [self._row_to_game_record(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_user_game_stats(self, user_id: str, game_type: str) -> Dict[str, Any]:
        """获取用户游戏统计"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_games,
                    SUM(coins_bet) as total_bet,
                    SUM(coins_won) as total_won,
                    SUM(coins_won - coins_bet) as net_profit,
                    AVG(coins_won - coins_bet) as avg_profit,
                    MAX(coins_won) as max_win,
                    MIN(coins_won - coins_bet) as worst_loss
                FROM game_records 
                WHERE user_id = ? AND game_type = ?
            ''', (user_id, game_type))
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_games': row['total_games'] or 0,
                    'total_bet': row['total_bet'] or 0,
                    'total_won': row['total_won'] or 0,
                    'net_profit': row['net_profit'] or 0,
                    'avg_profit': row['avg_profit'] or 0,
                    'max_win': row['max_win'] or 0,
                    'worst_loss': row['worst_loss'] or 0,
                    'win_rate': 0  # 需要根据具体游戏计算
                }
            else:
                return {
                    'total_games': 0,
                    'total_bet': 0,
                    'total_won': 0,
                    'net_profit': 0,
                    'avg_profit': 0,
                    'max_win': 0,
                    'worst_loss': 0,
                    'win_rate': 0
                }
        finally:
            conn.close()
    
    def _row_to_game_record(self, row) -> GameRecord:
        """将数据库行转换为GameRecord对象"""
        details = None
        if row['details']:
            try:
                details = json.loads(row['details'])
            except json.JSONDecodeError:
                details = None
        
        return GameRecord(
            id=row['id'],
            user_id=row['user_id'],
            game_type=row['game_type'],
            coins_bet=row['coins_bet'],
            coins_won=row['coins_won'],
            result=row['result'],
            details=details,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
    
    # ======================== 游戏房间管理 ========================
    
    def create_room(self, room: GameRoom) -> None:
        """创建游戏房间"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute('''
                INSERT INTO game_rooms (
                    id, game_type, channel_id, creator_id, creator_name, bet_amount,
                    status, max_players, min_players, players, game_data, settings,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                room.id,
                room.game_type,
                room.channel_id,
                room.creator_id,
                room.creator_name,
                room.bet_amount,
                room.status,
                room.max_players,
                room.min_players,
                json.dumps(room.players),
                json.dumps(room.game_data),
                json.dumps(room.settings),
                room.created_at or datetime.now()
            ))
            conn.commit()
        finally:
            conn.close()
    
    def update_room(self, room: GameRoom) -> None:
        """更新游戏房间"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute('''
                UPDATE game_rooms SET
                    status = ?, players = ?, game_data = ?, settings = ?,
                    started_at = ?, finished_at = ?
                WHERE id = ?
            ''', (
                room.status,
                json.dumps(room.players),
                json.dumps(room.game_data),
                json.dumps(room.settings),
                room.started_at,
                room.finished_at,
                room.id
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_room_by_id(self, room_id: str) -> Optional[GameRoom]:
        """根据ID获取游戏房间"""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute('SELECT * FROM game_rooms WHERE id = ?', (room_id,))
            row = cursor.fetchone()
            return self._row_to_game_room(row) if row else None
        finally:
            conn.close()
    
    def get_user_rooms(self, user_id: str, status: Optional[str] = None) -> List[GameRoom]:
        """获取用户参与的游戏房间"""
        conn = get_db_connection(self.db_path)
        try:
            if status:
                cursor = conn.execute('''
                    SELECT * FROM game_rooms 
                    WHERE (creator_id = ? OR players LIKE ?) AND status = ?
                    ORDER BY created_at DESC
                ''', (user_id, f'%{user_id}%', status))
            else:
                cursor = conn.execute('''
                    SELECT * FROM game_rooms 
                    WHERE creator_id = ? OR players LIKE ?
                    ORDER BY created_at DESC
                ''', (user_id, f'%{user_id}%'))
            
            return [self._row_to_game_room(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_channel_rooms(self, channel_id: str, game_type: Optional[str] = None, status: Optional[str] = None) -> List[GameRoom]:
        """获取频道内的游戏房间"""
        conn = get_db_connection(self.db_path)
        try:
            query = 'SELECT * FROM game_rooms WHERE channel_id = ?'
            params = [channel_id]
            
            if game_type:
                query += ' AND game_type = ?'
                params.append(game_type)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            
            cursor = conn.execute(query, params)
            return [self._row_to_game_room(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def delete_room(self, room_id: str) -> None:
        """删除游戏房间"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute('DELETE FROM game_rooms WHERE id = ?', (room_id,))
            conn.commit()
        finally:
            conn.close()
    
    def _row_to_game_room(self, row) -> GameRoom:
        """将数据库行转换为GameRoom对象"""
        try:
            players = json.loads(row['players']) if row['players'] else []
        except json.JSONDecodeError:
            players = []
        
        try:
            game_data = json.loads(row['game_data']) if row['game_data'] else {}
        except json.JSONDecodeError:
            game_data = {}
        
        try:
            settings = json.loads(row['settings']) if row['settings'] else {}
        except json.JSONDecodeError:
            settings = {}
        
        return GameRoom(
            id=row['id'],
            game_type=row['game_type'],
            channel_id=row['channel_id'],
            creator_id=row['creator_id'],
            creator_name=row['creator_name'],
            bet_amount=row['bet_amount'],
            status=row['status'],
            max_players=row['max_players'],
            min_players=row['min_players'],
            players=players,
            game_data=game_data,
            settings=settings,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            finished_at=datetime.fromisoformat(row['finished_at']) if row['finished_at'] else None
        )
