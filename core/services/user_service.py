from datetime import datetime, date
from typing import Optional, List, Dict, Any
from ..domain.models import User, LeaderboardEntry
from ..repositories.interfaces import UserRepository
from ..repositories.sqlite_user_repo import SqliteUserRepository


class UserService:
    """用户服务"""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def get_or_create_user(self, user_id: str, username: str) -> tuple[User, bool]:
        """获取或创建用户"""
        user = self.user_repo.get_by_id(user_id)
        is_new_user = False
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                coins=1000,  # 初始金币
                created_at=datetime.now()
            )
            self.user_repo.create(user)
            is_new_user = True
        elif user.username != username:
            # 更新用户名
            user.username = username
            self.user_repo.save(user)
        return user, is_new_user
    
    def add_coins(self, user_id: str, amount: int, reason: str = "") -> bool:
        """增加用户金币"""
        user = self.user_repo.get_by_id(user_id)
        if user:
            user.add_coins(amount)
            self.user_repo.save(user)
            return True
        return False
    
    def spend_coins(self, user_id: str, amount: int, reason: str = "") -> bool:
        """花费用户金币"""
        user = self.user_repo.get_by_id(user_id)
        if user and user.spend_coins(amount):
            self.user_repo.save(user)
            return True
        return False
    
    def transfer_coins(self, from_user_id: str, to_user_id: str, amount: int) -> bool:
        """转账金币"""
        from_user = self.user_repo.get_by_id(from_user_id)
        to_user = self.user_repo.get_by_id(to_user_id)
        
        if from_user and to_user and from_user.spend_coins(amount):
            to_user.add_coins(amount)
            self.user_repo.save(from_user)
            self.user_repo.save(to_user)
            return True
        return False
    
    def add_experience(self, user_id: str, exp: int) -> bool:
        """增加经验值，返回是否升级"""
        user = self.user_repo.get_by_id(user_id)
        if user:
            leveled_up = user.add_experience(exp)
            self.user_repo.save(user)
            return leveled_up
        return False
    
    def set_title(self, user_id: str, title: str) -> bool:
        """设置用户称号"""
        user = self.user_repo.get_by_id(user_id)
        if user:
            user.title = title
            self.user_repo.save(user)
            return True
        return False
    
    def get_leaderboard(self, limit: int = 10, offset: int = 0) -> List[LeaderboardEntry]:
        """获取排行榜"""
        return self.user_repo.get_leaderboard(limit, offset)
    
    def get_user_rank(self, user_id: str) -> Optional[int]:
        """获取用户排名"""
        return self.user_repo.get_user_rank(user_id)
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        user = self.user_repo.get_by_id(user_id)
        if user:
            rank = self.get_user_rank(user_id)
            return {
                'user': user,
                'rank': rank,
                'coins': user.coins,
                'profit_rate': (user.total_earned - user.total_spent) / max(user.total_spent, 1) if user.total_spent > 0 else 0
            }
        return None
