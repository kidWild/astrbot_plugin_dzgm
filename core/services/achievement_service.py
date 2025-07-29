from datetime import datetime
from typing import List, Dict, Any, Optional
from ..domain.models import Achievement, UserAchievement
from ..repositories.interfaces import AchievementRepository, UserAchievementRepository, UserRepository, GameRepository
from ..services.user_service import UserService


class AchievementService:
    """成就服务"""
    
    def __init__(self, 
                 achievement_repo: AchievementRepository,
                 user_achievement_repo: UserAchievementRepository,
                 user_service: UserService,
                 game_repo: Optional[GameRepository] = None):
        self.achievement_repo = achievement_repo
        self.user_achievement_repo = user_achievement_repo
        self.user_service = user_service
        self.game_repo = game_repo
    
    def initialize_achievements(self):
        """初始化默认成就"""
        default_achievements = self._get_default_achievements()
        for achievement in default_achievements:
            self.achievement_repo.create(achievement)
    
    def check_and_award_achievements(self, user_id: str, trigger_type: str, value: Any = None) -> List[Achievement]:
        """检查并颁发成就"""
        user = self.user_service.user_repo.get_by_id(user_id)
        if not user:
            return []
        
        newly_awarded = []
        achievements = self.achievement_repo.get_all()
        
        for achievement in achievements:
            # 跳过已获得的成就
            if self.user_achievement_repo.has_achievement(user_id, achievement.id):
                continue
            
            # 检查成就条件
            if self._check_achievement_condition(user, achievement, trigger_type, value):
                self._award_achievement(user_id, achievement)
                newly_awarded.append(achievement)
        
        return newly_awarded
    
    def _check_achievement_condition(self, user, achievement: Achievement, trigger_type: str, value: Any) -> bool:
        """检查成就条件是否满足"""
        if achievement.category == "金币" and trigger_type == "coins":
            if achievement.condition_type == "total_earned":
                return user.total_earned >= achievement.condition_value
            elif achievement.condition_type == "current_coins":
                return user.coins >= achievement.condition_value
            elif achievement.condition_type == "single_gain" and isinstance(value, int):
                return value >= achievement.condition_value
        
        elif achievement.category == "签到" and trigger_type == "check_in":
            if achievement.condition_type == "consecutive_days":
                return user.check_in_count >= achievement.condition_value
            elif achievement.condition_type == "total_check_ins":
                return user.total_check_ins >= achievement.condition_value
        
        elif achievement.category == "等级" and trigger_type == "level":
            if achievement.condition_type == "level":
                return user.level >= achievement.condition_value
        
        elif achievement.category == "游戏" and trigger_type == "game":
            # 游戏相关成就需要从游戏记录中查询
            if isinstance(value, dict) and self.game_repo:
                game_type = value.get('type', '')
                if achievement.condition_type == "roulette_win" and 'roulette_win' in game_type:
                    # 获取俄罗斯轮盘获胜次数
                    win_records = [r for r in self.game_repo.get_user_game_records(user.user_id, "russian_roulette") 
                                 if r.result == "win"]
                    return len(win_records) >= achievement.condition_value
                elif achievement.condition_type == "roulette_survive" and 'roulette_lose' in game_type:
                    # 获取俄罗斯轮盘生存次数（失败但参与的次数）
                    survive_records = [r for r in self.game_repo.get_user_game_records(user.user_id, "russian_roulette") 
                                     if r.result == "lose"]
                    return len(survive_records) >= achievement.condition_value
        
        return False
    
    def _award_achievement(self, user_id: str, achievement: Achievement):
        """颁发成就"""
        # 记录成就获得
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            achieved_at=datetime.now(),
            notified=False
        )
        self.user_achievement_repo.award_achievement(user_achievement)
        
        # 给予金币奖励
        if achievement.reward_coins > 0:
            self.user_service.add_coins(user_id, achievement.reward_coins, f"成就奖励：{achievement.name}")
        
        # 设置称号奖励
        if achievement.reward_title:
            self.user_service.set_title(user_id, achievement.reward_title)
    
    def get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        """获取用户成就"""
        return self.user_achievement_repo.get_user_achievements(user_id)
    
    def get_achievement_progress(self, user_id: str) -> Dict[str, Any]:
        """获取成就进度"""
        user = self.user_service.user_repo.get_by_id(user_id)
        if not user:
            return {}
        
        all_achievements = self.achievement_repo.get_all()
        user_achievements = self.user_achievement_repo.get_user_achievements(user_id)
        achieved_ids = {ua.achievement_id for ua in user_achievements}
        
        progress = {
            'total_achievements': len(all_achievements),
            'completed_achievements': len(achieved_ids),
            'completion_rate': len(achieved_ids) / len(all_achievements) if all_achievements else 0,
            'categories': {}
        }
        
        # 按分类统计
        for achievement in all_achievements:
            category = achievement.category
            if category not in progress['categories']:
                progress['categories'][category] = {
                    'total': 0,
                    'completed': 0,
                    'achievements': []
                }
            
            progress['categories'][category]['total'] += 1
            is_completed = achievement.id in achieved_ids
            if is_completed:
                progress['categories'][category]['completed'] += 1
            
            # 计算当前进度
            current_progress = self._calculate_current_progress(user, achievement)
            
            progress['categories'][category]['achievements'].append({
                'achievement': achievement,
                'completed': is_completed,
                'progress': current_progress,
                'progress_rate': min(current_progress / achievement.condition_value, 1.0) if achievement.condition_value > 0 else 1.0
            })
        
        return progress
    
    def _calculate_current_progress(self, user, achievement: Achievement) -> int:
        """计算当前成就进度"""
        if achievement.category == "金币":
            if achievement.condition_type == "total_earned":
                return user.total_earned
            elif achievement.condition_type == "current_coins":
                return user.coins
        elif achievement.category == "签到":
            if achievement.condition_type == "consecutive_days":
                return user.check_in_count
            elif achievement.condition_type == "total_check_ins":
                return user.total_check_ins
        elif achievement.category == "等级":
            if achievement.condition_type == "level":
                return user.level
        
        return 0
    
    def get_unnotified_achievements(self, user_id: str) -> List[Achievement]:
        """获取未通知的新成就"""
        user_achievements = self.user_achievement_repo.get_unnotified_achievements(user_id)
        achievements = []
        for ua in user_achievements:
            achievement = self.achievement_repo.get_by_id(ua.achievement_id)
            if achievement:
                achievements.append(achievement)
                # 标记为已通知
                self.user_achievement_repo.mark_as_notified(user_id, ua.achievement_id)
        return achievements
    
    def _get_default_achievements(self) -> List[Achievement]:
        """获取默认成就列表"""
        return [
            # 金币类成就
            Achievement("first_hundred", "小富即安", "拥有100金币", "金币", "current_coins", 100, 50, "小康"),
            Achievement("first_thousand", "财源广进", "拥有1000金币", "金币", "current_coins", 1000, 200, "富足"),
            Achievement("first_ten_thousand", "财富自由", "拥有10000金币", "金币", "current_coins", 10000, 1000, "富豪"),
            Achievement("millionaire", "百万富翁", "拥有100万金币", "金币", "current_coins", 1000000, 50000, "百万富翁"),
            Achievement("earn_thousand", "积少成多", "累计获得1000金币", "金币", "total_earned", 1000, 100),
            Achievement("earn_hundred_thousand", "财富积累", "累计获得10万金币", "金币", "total_earned", 100000, 5000),
            Achievement("single_gain_1000", "一夜暴富", "单次获得1000金币", "金币", "single_gain", 1000, 500),
            
            # 签到类成就
            Achievement("check_in_7", "每日一签", "连续签到7天", "签到", "consecutive_days", 7, 300, "守时"),
            Achievement("check_in_30", "守约之人", "连续签到30天", "签到", "consecutive_days", 30, 1500, "守约之人"),
            Achievement("check_in_100", "坚持不懈", "连续签到100天", "签到", "consecutive_days", 100, 8000, "坚持不懈"),
            Achievement("check_in_365", "签到达人", "连续签到365天", "签到", "consecutive_days", 365, 50000, "签到达人"),
            Achievement("total_check_in_50", "签到爱好者", "累计签到50次", "签到", "total_check_ins", 50, 1000),
            Achievement("total_check_in_200", "打卡专家", "累计签到200次", "签到", "total_check_ins", 200, 5000),
            
            # 等级类成就
            Achievement("level_5", "初出茅庐", "达到5级", "等级", "level", 5, 200),
            Achievement("level_10", "小有成就", "达到10级", "等级", "level", 10, 500, "小有成就"),
            Achievement("level_20", "经验丰富", "达到20级", "等级", "level", 20, 1500, "老手"),
            Achievement("level_50", "资深玩家", "达到50级", "等级", "level", 50, 10000, "资深玩家"),
            
            # 游戏类成就（俄罗斯轮盘）
            Achievement("roulette_first_win", "初战告捷", "俄罗斯轮盘首次获胜", "游戏", "roulette_win", 1, 100),
            Achievement("roulette_win_10", "幸运之星", "俄罗斯轮盘获胜10次", "游戏", "roulette_win", 10, 500, "幸运儿"),
            Achievement("roulette_survivor", "死里逃生", "俄罗斯轮盘生存100次", "游戏", "roulette_survive", 100, 2000, "幸存者"),
        ]
