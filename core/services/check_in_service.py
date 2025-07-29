import random
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, Dict, Any
from ..domain.models import User, CheckInRecord
from ..repositories.interfaces import UserRepository, CheckInRepository
from ..services.user_service import UserService
from astrbot.api import logger, AstrBotConfig


class CheckInService:
    """签到服务"""
    
    def __init__(self, user_service: UserService, check_in_repo: CheckInRepository):
        self.user_service = user_service
        self.check_in_repo = check_in_repo
        
        # 签到阶梯奖励配置
        self.base_reward_tiers = [
            (1, 50, 200),       # 1-6天: 50-200
            (7, 80, 250),       # 7-13天: 80-250
            (14, 120, 300),     # 14-29天: 120-300
            (30, 150, 400),     # 30-59天: 150-400
            (60, 200, 500),     # 60-89天: 200-500
            (90, 250, 600),     # 90-179天: 250-600
            (180, 300, 800),    # 180-364天: 300-800
            (365, 400, 1000),   # 365天以上: 400-1000
        ]
        self.consecutive_bonuses = {
            7: 500,     # 连续7天奖励
            14: 1000,   # 连续14天奖励  
            30: 3000,   # 连续30天奖励
            60: 8000,   # 连续60天奖励
            90: 20000,  # 连续90天奖励
            180: 50000, # 连续180天奖励
            365: 100000 # 连续365天奖励
        }
    
    def _check_check_in_title(self, consecutive_days: int) -> Optional[str]:
        """检查签到称号"""
        if consecutive_days >= 365:
            return "签到达人"
        elif consecutive_days >= 180:
            return "坚持不懈"
        elif consecutive_days >= 90:
            return "持之以恒"
        elif consecutive_days >= 30:
            return "守约之人"
        elif consecutive_days >= 7:
            return "每日一签"
        return None 
    
    def can_check_in(self, user: User) -> bool:
        """检查用户是否可以签到"""
        return user.can_check_in()
    
    def check_in(self, user_id: str, username: str) -> Dict[str, Any]:
        """用户签到"""
        is_new_user = False
        user, is_new_user = self.user_service.get_or_create_user(user_id, username)
        
        if not self.can_check_in(user):
            return {
                'success': False,
                'message': '今天已经签到过了！',
                'next_check_in': self._get_next_check_in_time(user)
            }
        
        # 计算连续签到天数
        consecutive_days = self._calculate_consecutive_days(user)
        
        # 计算奖励
        base_reward_range = self._get_base_reward_range(consecutive_days)
        base_reward = random.randint(*base_reward_range)
        bonus_reward = self._calculate_bonus_reward(consecutive_days)
        total_reward = base_reward + bonus_reward
        
        # 更新用户数据
        user.last_check_in = datetime.now()
        user.check_in_count = consecutive_days
        user.total_check_ins += 1
        user.add_coins(total_reward)
        
        # 保存用户数据
        self.user_service.user_repo.save(user)
        
        # 创建签到记录
        check_in_record = CheckInRecord(
            user_id=user_id,
            check_in_date=date.today(),
            coins_earned=base_reward,
            consecutive_days=consecutive_days,
            bonus_coins=bonus_reward
        )
        self.check_in_repo.create_record(check_in_record)
        
        # 检查是否获得称号
        new_title = self._check_check_in_title(consecutive_days)
        if new_title and user.title != new_title:
            user.title = new_title
            self.user_service.user_repo.save(user)
        
        return {
            'success': True,
            'base_reward': base_reward,
            'bonus_reward': bonus_reward,
            'total_reward': total_reward,
            'consecutive_days': consecutive_days,
            'total_check_ins': user.total_check_ins,
            'current_coins': user.coins,
            'new_title': new_title,
            'is_new_user': is_new_user
        }
    
    def _calculate_consecutive_days(self, user: User) -> int:
        """计算连续签到天数"""
        if not user.last_check_in:
            return 1
        
        today = date.today()
        last_check_in_date = user.last_check_in.date()
        
        # 如果昨天签到了，连续天数+1
        if (today - last_check_in_date).days == 1:
            return user.check_in_count + 1
        # 如果是今天签到（不应该发生，但防御性编程）
        elif (today - last_check_in_date).days == 0:
            logger.warning(f"用户 {user.user_id} 在今天完成了重复签到？连续天数保持不变: {user.check_in_count}")
            return user.check_in_count
        # 如果中断了，重新开始
        else:
            return 1
    
    def _calculate_bonus_reward(self, consecutive_days: int) -> int:
        """计算连续签到奖励"""
        bonus = 0
        for days, reward in self.consecutive_bonuses.items():
            if consecutive_days >= days:
                # 只在刚好达到里程碑时给予奖励
                if consecutive_days == days:
                    bonus += reward
        return bonus
    
    def _get_next_check_in_time(self, user: User) -> datetime:
        """获取下次可签到时间"""
        if user.last_check_in:
            next_day = user.last_check_in.date() + timedelta(days=1)
            return datetime.combine(next_day, datetime.min.time())
        return datetime.now()
    
    def get_check_in_stats(self, user_id: str) -> Dict[str, Any]:
        """获取签到统计"""
        user = self.user_service.user_repo.get_by_id(user_id)
        if not user:
            return {}
        
        records = self.check_in_repo.get_user_check_ins(user_id, 30)
        total_check_ins = self.check_in_repo.get_total_check_ins(user_id)
        
        total_coins_from_check_in = sum(r.coins_earned + r.bonus_coins for r in records)
        
        return {
            'consecutive_days': user.check_in_count,
            'total_check_ins': total_check_ins,
            'can_check_in': self.can_check_in(user),
            'next_check_in': self._get_next_check_in_time(user),
            'total_coins_earned': total_coins_from_check_in,
            'recent_records': records[:7]  # 最近7天记录
        }
    def _get_base_reward_range(self, consecutive_days: int) -> Tuple[int, int]:
        """根据连续签到天数获取基础奖励范围"""
        for threshold, min_reward, max_reward in reversed(self.base_reward_tiers):
            if consecutive_days >= threshold:
                return (min_reward, max_reward)
        # 默认返回最低档
        return (50, 200)
