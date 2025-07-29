from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..core.domain.models import GameRoom


class GameEngine(ABC):
    """游戏引擎基类"""
    
    @property
    @abstractmethod
    def game_type(self) -> str:
        """游戏类型标识"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """游戏显示名称"""
        pass
    
    @property
    @abstractmethod
    def min_players(self) -> int:
        """最小玩家数"""
        pass
    
    @property
    @abstractmethod
    def max_players(self) -> int:
        """最大玩家数"""
        pass
    
    @property
    @abstractmethod
    def min_bet(self) -> int:
        """最小下注金额"""
        pass
    
    @property
    @abstractmethod
    def max_bet(self) -> int:
        """最大下注金额"""
        pass
    
    @abstractmethod
    def get_game_rules(self) -> str:
        """获取游戏规则说明"""
        pass
    
    @abstractmethod
    def initialize_game_data(self, room: GameRoom) -> Dict[str, Any]:
        """初始化游戏数据"""
        pass
    
    @abstractmethod
    def can_start_game(self, room: GameRoom) -> bool:
        """检查是否可以开始游戏"""
        pass
    
    @abstractmethod
    def start_game(self, room: GameRoom) -> Dict[str, Any]:
        """开始游戏"""
        pass
    
    @abstractmethod
    def process_action(self, room: GameRoom, user_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理游戏动作"""
        pass
    
    @abstractmethod
    def get_game_status(self, room: GameRoom) -> str:
        """获取游戏状态显示"""
        pass
    
    @abstractmethod
    def is_game_finished(self, room: GameRoom) -> bool:
        """检查游戏是否结束"""
        pass
    
    @abstractmethod
    def get_game_result(self, room: GameRoom) -> Dict[str, Any]:
        """获取游戏结果"""
        pass
