from abc import ABC, abstractmethod
from typing import List, Optional
from ..domain.models import User, Achievement, UserAchievement, CheckInRecord, GameRecord, GameRoom, LeaderboardEntry


class UserRepository(ABC):
    """用户仓储接口"""
    
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def save(self, user: User) -> None:
        pass
    
    @abstractmethod
    def create(self, user: User) -> None:
        pass
    
    @abstractmethod
    def get_leaderboard(self, limit: int = 10, offset: int = 0) -> List[LeaderboardEntry]:
        pass
    
    @abstractmethod
    def get_user_rank(self, user_id: str) -> Optional[int]:
        pass


class AchievementRepository(ABC):
    """成就仓储接口"""
    
    @abstractmethod
    def get_all(self) -> List[Achievement]:
        pass
    
    @abstractmethod
    def get_by_id(self, achievement_id: str) -> Optional[Achievement]:
        pass
    
    @abstractmethod
    def get_by_category(self, category: str) -> List[Achievement]:
        pass
    
    @abstractmethod
    def create(self, achievement: Achievement) -> None:
        pass


class UserAchievementRepository(ABC):
    """用户成就仓储接口"""
    
    @abstractmethod
    def get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        pass
    
    @abstractmethod
    def has_achievement(self, user_id: str, achievement_id: str) -> bool:
        pass
    
    @abstractmethod
    def award_achievement(self, user_achievement: UserAchievement) -> None:
        pass
    
    @abstractmethod
    def get_unnotified_achievements(self, user_id: str) -> List[UserAchievement]:
        pass
    
    @abstractmethod
    def mark_as_notified(self, user_id: str, achievement_id: str) -> None:
        pass


class CheckInRepository(ABC):
    """签到仓储接口"""
    
    @abstractmethod
    def create_record(self, record: CheckInRecord) -> None:
        pass
    
    @abstractmethod
    def get_user_check_ins(self, user_id: str, limit: int = 30) -> List[CheckInRecord]:
        pass
    
    @abstractmethod
    def get_total_check_ins(self, user_id: str) -> int:
        pass


class GameRepository(ABC):
    """游戏记录和房间仓储接口"""
    
    # 游戏记录相关
    @abstractmethod
    def create_record(self, record: GameRecord) -> None:
        pass
    
    @abstractmethod
    def get_user_game_records(self, user_id: str, game_type: Optional[str] = None, limit: int = 50) -> List[GameRecord]:
        pass
    
    @abstractmethod
    def get_user_game_stats(self, user_id: str, game_type: str) -> dict:
        pass
    
    # 游戏房间相关
    @abstractmethod
    def create_room(self, room: GameRoom) -> None:
        """创建游戏房间"""
        pass
    
    @abstractmethod
    def update_room(self, room: GameRoom) -> None:
        """更新游戏房间"""
        pass
    
    @abstractmethod
    def get_room_by_id(self, room_id: str) -> Optional[GameRoom]:
        """根据ID获取游戏房间"""
        pass
    
    @abstractmethod
    def get_user_rooms(self, user_id: str, status: Optional[str] = None) -> List[GameRoom]:
        """获取用户参与的游戏房间"""
        pass
    
    @abstractmethod
    def get_channel_rooms(self, channel_id: str, game_type: Optional[str] = None, status: Optional[str] = None) -> List[GameRoom]:
        """获取频道内的游戏房间"""
        pass
    
    @abstractmethod
    def delete_room(self, room_id: str) -> None:
        """删除游戏房间"""
        pass
