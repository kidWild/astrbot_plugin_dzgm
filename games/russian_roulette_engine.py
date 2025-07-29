import random
from typing import Dict, Any, List, Optional
from ..core.domain.models import GameRoom
from .game_engine import GameEngine


class RussianRouletteEngine(GameEngine):
    """俄罗斯轮盘游戏引擎"""
    
    @property
    def game_type(self) -> str:
        return "russian_roulette"
    
    @property
    def display_name(self) -> str:
        return "俄罗斯轮盘"
    
    @property
    def min_players(self) -> int:
        return 2
    
    @property
    def max_players(self) -> int:
        return 6
    
    @property
    def min_bet(self) -> int:
        return 100
    
    @property
    def max_bet(self) -> int:
        return 10000
    
    def get_game_rules(self) -> str:
        """获取游戏规则说明"""
        return (
            f"🎲 {self.display_name}游戏规则 🎲\n\n"
            f"📝 基本规则:\n"
            f"• 转轮有6个位置，其中1个位置有子弹\n"
            f"• 玩家轮流开枪，每次可开1-3枪\n"
            f"• 中弹的玩家出局，最后存活者获得所有金币\n"
            f"• 玩家数量: {self.min_players}-{self.max_players} 人\n"
            f"• 下注范围: {self.min_bet}-{self.max_bet} 金币\n\n"
            f"⚠️  注意事项:\n"
            f"• 游戏开始后无法退出\n"
            f"• 创建游戏时立即扣除金币\n"
            f"• 游戏取消会退还所有金币"
        )
    
    def initialize_game_data(self, room: GameRoom) -> Dict[str, Any]:
        """初始化游戏数据"""
        return {
            'bullet_position': 0,  # 子弹位置，游戏开始时随机设置
            'current_position': 1,  # 当前转轮位置
            'current_player_index': 0,  # 当前玩家索引
            'chamber_count': 6,  # 转轮弹仓数量
            'bullets_count': 1  # 子弹数量
        }
    
    def can_start_game(self, room: GameRoom) -> bool:
        """检查是否可以开始游戏"""
        return len(room.players) >= self.min_players
    
    def start_game(self, room: GameRoom) -> Dict[str, Any]:
        """开始游戏"""
        # 随机设置子弹位置
        room.game_data['bullet_position'] = random.randint(1, room.game_data['chamber_count'])
        room.game_data['current_position'] = 1
        room.game_data['current_player_index'] = 0
        
        # 随机打乱玩家顺序
        random.shuffle(room.players)
        
        # 初始化玩家状态
        for player in room.players:
            player['is_alive'] = True
            player['shots_fired'] = 0
        
        current_player = room.players[room.game_data['current_player_index']]
        player_list = [p['username'] for p in room.players]
        
        return {
            'message': (
                f"🔥 {self.display_name} #{room.id} 开始！\n\n"
                f"参与玩家: {', '.join(player_list)}\n"
                f"奖池金额: {room.bet_amount * len(room.players)} 金币\n"
                f"转轮弹仓: {room.game_data['chamber_count']} 个位置，{room.game_data['bullets_count']} 颗子弹\n\n"
                f"🎯 轮到 {current_player['username']} 开枪！"
            )
        }
    
    def process_action(self, room: GameRoom, user_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理游戏动作"""
        if action != "shoot":
            return {
                'success': False,
                'message': '无效的游戏动作！'
            }
        
        # 检查是否轮到该玩家
        current_player = room.players[room.game_data['current_player_index']]
        if current_player['user_id'] != user_id:
            return {
                'success': False,
                'message': f'现在是 {current_player["username"]} 的回合！'
            }
        
        # 获取开枪数量
        shots = params.get('shots', 1) if params else 1
        if shots < 1 or shots > 3:
            return {
                'success': False,
                'message': '每次可以开1-3枪！'
            }
        
        # 执行开枪
        result_messages = []
        is_dead = False
        
        for i in range(shots):
            if room.game_data['current_position'] == room.game_data['bullet_position']:
                # 中弹了
                is_dead = True
                current_player['is_alive'] = False
                result_messages.append(f"💥 第{i+1}枪：{current_player['username']} 中弹身亡！")
                break
            else:
                # 空枪
                result_messages.append(f"🔫 第{i+1}枪：空枪，{current_player['username']} 安全！")
                room.game_data['current_position'] += 1
                if room.game_data['current_position'] > room.game_data['chamber_count']:
                    room.game_data['current_position'] = 1
        
        current_player['shots_fired'] += shots
        
        # 检查游戏是否结束
        alive_players = [p for p in room.players if p['is_alive']]
        
        if is_dead or len(alive_players) <= 1:
            # 游戏结束，在这里不处理结束逻辑，由GameService处理
            return {
                'success': True,
                'game_continues': False,
                'message': '\n'.join(result_messages)
            }
        else:
            # 切换到下一个玩家
            self._next_player(room)
            
            next_player = room.players[room.game_data['current_player_index']]
            result_messages.append(f"\n轮到 {next_player['username']} 开枪！")
            
            return {
                'success': True,
                'game_continues': True,
                'message': '\n'.join(result_messages) + f"\n\n{self.get_game_status(room)}"
            }
    
    def get_game_status(self, room: GameRoom) -> str:
        """获取游戏状态显示"""
        if room.status != 'playing':
            return "游戏未在进行中"
        
        alive_players = [p for p in room.players if p['is_alive']]
        dead_players = [p for p in room.players if not p['is_alive']]
        current_player = room.players[room.game_data['current_player_index']]
        
        message = f"🎲 {self.display_name} #{room.id} 进行中\n\n"
        message += f"奖池: {room.bet_amount * len(room.players)} 金币\n"
        message += f"转轮位置: {room.game_data['current_position']}/{room.game_data['chamber_count']}\n\n"
        
        message += f"🟢 存活玩家 ({len(alive_players)}):\n"
        for player in alive_players:
            marker = "👉 " if player['user_id'] == current_player['user_id'] else "   "
            message += f"{marker}{player['username']} (开枪{player['shots_fired']}次)\n"
        
        if dead_players:
            message += f"\n💀 阵亡玩家 ({len(dead_players)}):\n"
            for player in dead_players:
                message += f"   {player['username']} (开枪{player['shots_fired']}次)\n"
        
        message += f"\n🎯 等待 {current_player['username']} 开枪"
        return message
    
    def is_game_finished(self, room: GameRoom) -> bool:
        """检查游戏是否结束"""
        alive_players = [p for p in room.players if p['is_alive']]
        return len(alive_players) <= 1
    
    def get_game_result(self, room: GameRoom) -> Dict[str, Any]:
        """获取游戏结果"""
        alive_players = [p for p in room.players if p['is_alive']]
        
        result = {
            'total_players': len(room.players),
            'bullet_position': room.game_data['bullet_position'],
            'final_position': room.game_data['current_position'],
            'winners': []
        }
        
        if alive_players:
            result['winners'] = [p['user_id'] for p in alive_players]
            result['winner_names'] = [p['username'] for p in alive_players]
        
        return result
    
    def _next_player(self, room: GameRoom) -> None:
        """切换到下一个活着的玩家"""
        attempts = 0
        while attempts < len(room.players):
            room.game_data['current_player_index'] = (room.game_data['current_player_index'] + 1) % len(room.players)
            if room.players[room.game_data['current_player_index']]['is_alive']:
                break
            attempts += 1
