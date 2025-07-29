from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any, List


@dataclass
class User:
    """用户领域模型"""
    user_id: str
    username: str
    coins: int = 0
    total_earned: int = 0  # 历史总收入
    total_spent: int = 0   # 历史总支出
    check_in_count: int = 0  # 连续签到天数
    last_check_in: Optional[datetime] = None
    total_check_ins: int = 0  # 总签到次数
    level: int = 1
    experience: int = 0
    title: str = "新人"  # 当前称号
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def can_check_in(self) -> bool:
        """检查是否可以签到"""
        if not self.last_check_in:
            return True
        # 检查是否已经过了一天
        now = datetime.now()
        return (now.date() - self.last_check_in.date()).days >= 1
    
    def add_coins(self, amount: int) -> None:
        """增加金币"""
        self.coins += amount
        self.total_earned += amount
    
    def spend_coins(self, amount: int) -> bool:
        """花费金币，返回是否成功"""
        if self.coins >= amount:
            self.coins -= amount
            self.total_spent += amount
            return True
        return False
    
    def add_experience(self, exp: int) -> bool:
        """增加经验值，返回是否升级"""
        self.experience += exp
        # 简单的升级算法：每级需要 100 * level 经验
        exp_needed = 100 * self.level
        if self.experience >= exp_needed:
            self.level += 1
            self.experience -= exp_needed
            return True
        return False


@dataclass
class Achievement:
    """成就领域模型"""
    id: str
    name: str
    description: str
    category: str  # 分类：签到、游戏、金币等
    condition_type: str  # 条件类型：count、amount、streak等
    condition_value: int  # 条件值
    reward_coins: int  # 金币奖励
    reward_title: Optional[str] = None  # 称号奖励
    icon: Optional[str] = None  # 成就图标
    is_hidden: bool = False  # 是否隐藏成就
    created_at: Optional[datetime] = None


@dataclass
class UserAchievement:
    """用户成就关联模型"""
    user_id: str
    achievement_id: str
    achieved_at: datetime
    notified: bool = False  # 是否已通知用户


@dataclass
class CheckInRecord:
    """签到记录模型"""
    user_id: str
    check_in_date: date  # 使用date类型而不是datetime
    coins_earned: int
    consecutive_days: int
    bonus_coins: int = 0  # 连续签到奖励金币


@dataclass
class GameRecord:
    """游戏记录模型"""
    id: Optional[int] = None
    user_id: str = ""
    game_type: str = ""  # 游戏类型：roulette等
    coins_bet: int = 0  # 下注金币
    coins_won: int = 0  # 赢得金币
    result: str = ""  # 游戏结果
    details: Optional[Dict[str, Any]] = None  # 游戏详情(JSON)
    created_at: Optional[datetime] = None


@dataclass
class GameRoom:
    """通用游戏房间模型"""
    id: str  # 游戏房间ID
    game_type: str  # 游戏类型：russian_roulette, blackjack, etc.
    channel_id: str  # 群聊ID或私聊ID
    creator_id: str  # 创建者ID
    creator_name: str  # 创建者名称
    bet_amount: int  # 下注金额
    status: str = 'waiting'  # 游戏状态：waiting, playing, finished, cancelled
    max_players: int = 6  # 最大玩家数
    min_players: int = 2  # 最小玩家数
    players: List[Dict[str, Any]] = field(default_factory=list)  # 参与玩家列表
    game_data: Dict[str, Any] = field(default_factory=dict)  # 游戏特定数据
    settings: Dict[str, Any] = field(default_factory=dict)  # 游戏设置
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


@dataclass
class LeaderboardEntry:
    """排行榜条目"""
    rank: int
    user_id: str
    username: str
    score: int  # 分数（金币数量）
    title: str = "新人"
