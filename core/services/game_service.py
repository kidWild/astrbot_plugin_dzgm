import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from ..domain.models import GameRoom, GameRecord
from ..repositories.interfaces import GameRepository
from ..services.user_service import UserService
from ..services.achievement_service import AchievementService
from ...games.game_engine import GameEngine


class GameService:
    """统一游戏服务"""
    
    def __init__(self, 
                 game_repo: GameRepository,
                 user_service: UserService,
                 achievement_service: Optional[AchievementService] = None):
        self.game_repo = game_repo
        self.user_service = user_service
        self.achievement_service = achievement_service
        self.game_engines: Dict[str, GameEngine] = {}
    
    def register_game_engine(self, engine: GameEngine) -> None:
        """注册游戏引擎"""
        self.game_engines[engine.game_type] = engine
    
    def get_available_games(self) -> List[Dict[str, Any]]:
        """获取可用的游戏列表"""
        return [
            {
                'type': engine.game_type,
                'name': engine.display_name,
                'min_players': engine.min_players,
                'max_players': engine.max_players,
                'min_bet': engine.min_bet,
                'max_bet': engine.max_bet
            }
            for engine in self.game_engines.values()
        ]
    
    def create_room(self, game_type: str, channel_id: str, creator_id: str, creator_name: str, bet_amount: int) -> Dict[str, Any]:
        """创建游戏房间"""
        engine = self.game_engines.get(game_type)
        if not engine:
            return {
                'success': False,
                'message': f'不支持的游戏类型：{game_type}'
            }
        
        # 验证下注金额
        if bet_amount < engine.min_bet:
            return {
                'success': False,
                'message': f'最小下注金额为 {engine.min_bet} 金币'
            }
        
        if bet_amount > engine.max_bet:
            return {
                'success': False,
                'message': f'最大下注金额为 {engine.max_bet} 金币'
            }
        
        # 检查用户金币
        user, _ = self.user_service.get_or_create_user(creator_id, creator_name)
        if user.coins < bet_amount:
            return {
                'success': False,
                'message': f'金币不足！当前金币：{user.coins}，需要：{bet_amount}'
            }
        
        # 检查用户是否已有活跃房间（个人限制而非群限制）
        user_active_rooms = self.game_repo.get_user_rooms(creator_id, 'waiting') + self.game_repo.get_user_rooms(creator_id, 'playing')
        if user_active_rooms:
            return {
                'success': False,
                'message': '你已有活跃的游戏房间，请先完成或取消现有游戏。'
            }
        
        # 创建游戏房间
        room_id = str(uuid.uuid4())[:8]
        room = GameRoom(
            id=room_id,
            game_type=game_type,
            channel_id=channel_id,
            creator_id=creator_id,
            creator_name=creator_name,
            bet_amount=bet_amount,
            status='waiting',
            max_players=engine.max_players,
            min_players=engine.min_players,
            players=[{
                'user_id': creator_id,
                'username': creator_name,
                'joined_at': datetime.now().isoformat()
            }],
            created_at=datetime.now()
        )
        
        # 初始化游戏数据
        room.game_data = engine.initialize_game_data(room)
        
        # 扣除创建者金币
        self.user_service.spend_coins(creator_id, bet_amount, f"{engine.display_name}游戏下注 #{room_id}")
        
        # 保存房间
        self.game_repo.create_room(room)
        
        return {
            'success': True,
            'room_id': room_id,
            'message': self._build_room_created_message(room, engine)
        }
    
    def join_room(self, room_id: str, user_id: str, username: str) -> Dict[str, Any]:
        """加入游戏房间"""
        room = self.game_repo.get_room_by_id(room_id)
        if not room:
            return {
                'success': False,
                'message': '游戏房间不存在！'
            }
        
        engine = self.game_engines.get(room.game_type)
        if not engine:
            return {
                'success': False,
                'message': '游戏引擎不可用！'
            }
        
        if room.status != 'waiting':
            return {
                'success': False,
                'message': '游戏已开始或已结束，无法加入！'
            }
        
        # 检查是否已加入
        for player in room.players:
            if player['user_id'] == user_id:
                return {
                    'success': False,
                    'message': '你已经加入了这个游戏！'
                }
        
        # 检查玩家数量限制
        if len(room.players) >= room.max_players:
            return {
                'success': False,
                'message': f'游戏人数已满！（{room.max_players}人）'
            }
        
        # 检查用户金币
        user, _ = self.user_service.get_or_create_user(user_id, username)
        if user.coins < room.bet_amount:
            return {
                'success': False,
                'message': f'金币不足！当前金币：{user.coins}，需要：{room.bet_amount}'
            }
        
        # 扣除金币并加入游戏
        self.user_service.spend_coins(user_id, room.bet_amount, f"{engine.display_name}游戏下注 #{room_id}")
        
        room.players.append({
            'user_id': user_id,
            'username': username,
            'joined_at': datetime.now().isoformat()
        })
        
        # 更新房间
        self.game_repo.update_room(room)
        
        can_start = len(room.players) >= room.min_players
        
        return {
            'success': True,
            'can_start': can_start,
            'message': self._build_player_joined_message(room, username, can_start, engine)
        }
    
    def start_room(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """开始游戏"""
        room = self.game_repo.get_room_by_id(room_id)
        if not room:
            return {
                'success': False,
                'message': '游戏房间不存在！'
            }
        
        engine = self.game_engines.get(room.game_type)
        if not engine:
            return {
                'success': False,
                'message': '游戏引擎不可用！'
            }
        
        # 只有创建者可以开始游戏
        if room.creator_id != user_id:
            return {
                'success': False,
                'message': '只有游戏创建者可以开始游戏！'
            }
        
        if room.status != 'waiting':
            return {
                'success': False,
                'message': '游戏已开始或已结束！'
            }
        
        if not engine.can_start_game(room):
            return {
                'success': False,
                'message': f'至少需要 {room.min_players} 名玩家才能开始游戏！'
            }
        
        # 开始游戏
        room.status = 'playing'
        room.started_at = datetime.now()
        
        # 调用游戏引擎开始游戏
        start_result = engine.start_game(room)
        
        # 更新房间
        self.game_repo.update_room(room)
        
        return {
            'success': True,
            'message': start_result.get('message', '游戏开始！')
        }
    
    def process_game_action(self, room_id: str, user_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理游戏动作"""
        room = self.game_repo.get_room_by_id(room_id)
        if not room:
            return {
                'success': False,
                'message': '游戏房间不存在！'
            }
        
        engine = self.game_engines.get(room.game_type)
        if not engine:
            return {
                'success': False,
                'message': '游戏引擎不可用！'
            }
        
        if room.status != 'playing':
            return {
                'success': False,
                'message': '游戏未开始或已结束！'
            }
        
        # 调用游戏引擎处理动作
        result = engine.process_action(room, user_id, action, params or {})
        
        # 检查游戏是否结束
        if engine.is_game_finished(room):
            self._finish_game(room, engine)
        else:
            # 更新房间状态
            self.game_repo.update_room(room)
        
        return result
    
    def cancel_room(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """取消游戏房间"""
        room = self.game_repo.get_room_by_id(room_id)
        if not room:
            return {
                'success': False,
                'message': '游戏房间不存在！'
            }
        
        if room.creator_id != user_id:
            return {
                'success': False,
                'message': '只有游戏创建者可以取消游戏！'
            }
        
        if room.status == 'playing':
            return {
                'success': False,
                'message': '游戏已开始，无法取消！'
            }
        
        # 退还所有玩家的金币
        for player in room.players:
            self.user_service.add_coins(player['user_id'], room.bet_amount, f"游戏取消退款 #{room_id}")
        
        # 删除房间
        self.game_repo.delete_room(room_id)
        
        return {
            'success': True,
            'message': f'游戏房间 #{room_id} 已取消，所有玩家的金币已退还。'
        }
    
    def get_room_list(self, channel_id: str, game_type: Optional[str] = None) -> str:
        """获取房间列表"""
        waiting_rooms = self.game_repo.get_channel_rooms(channel_id, game_type, 'waiting')
        playing_rooms = self.game_repo.get_channel_rooms(channel_id, game_type, 'playing')
        
        if not waiting_rooms and not playing_rooms:
            return "📋 当前没有游戏房间"
        
        message = "🎮 游戏房间列表\n\n"
        
        if playing_rooms:
            message += "🔥 进行中的游戏:\n"
            for room in playing_rooms:
                engine = self.game_engines.get(room.game_type)
                if engine:
                    message += f"🎯 {engine.display_name} #{room.id}\n"
                    message += f"   {engine.get_game_status(room)}\n\n"
        
        if waiting_rooms:
            message += "⏳ 等待中的游戏:\n"
            for room in waiting_rooms:
                engine = self.game_engines.get(room.game_type)
                if engine:
                    message += f"🎮 {engine.display_name} #{room.id}\n"
                    message += f"   创建者: {room.creator_name}\n"
                    message += f"   下注: {room.bet_amount} 金币\n"
                    message += f"   玩家: {len(room.players)}/{room.max_players}\n\n"
        
        return message
    
    def _finish_game(self, room: GameRoom, engine: GameEngine) -> None:
        """结束游戏"""
        room.status = 'finished'
        room.finished_at = datetime.now()
        
        # 获取游戏结果
        game_result = engine.get_game_result(room)
        
        # 分发奖金和记录游戏
        total_pot = room.bet_amount * len(room.players)
        winners = game_result.get('winners', [])
        
        if winners:
            # 平分奖金给获胜者
            prize_per_winner = total_pot // len(winners)
            for winner_id in winners:
                self.user_service.add_coins(winner_id, prize_per_winner, f"{engine.display_name}游戏获胜 #{room.id}")
        
        # 记录游戏结果
        for player in room.players:
            is_winner = player['user_id'] in winners
            game_record = GameRecord(
                user_id=player['user_id'],
                game_type=room.game_type,
                coins_bet=room.bet_amount,
                coins_won=prize_per_winner if is_winner else 0,
                result="win" if is_winner else "lose",
                details={
                    'room_id': room.id,
                    'total_players': len(room.players),
                    'game_result': game_result
                },
                created_at=datetime.now()
            )
            self.game_repo.create_record(game_record)
            
            # 检查成就
            if self.achievement_service:
                achievement_data = {
                    'type': f'{room.game_type}_{"win" if is_winner else "lose"}',
                    'value': 1
                }
                achievements = self.achievement_service.check_and_award_achievements(
                    player['user_id'], "game", achievement_data
                )
        
        # 更新房间
        self.game_repo.update_room(room)
    
    def _build_room_created_message(self, room: GameRoom, engine: GameEngine) -> str:
        """构建房间创建消息"""
        return (
            f"🎮 {engine.display_name} #{room.id} 已创建！\n\n"
            f"创建者: {room.creator_name}\n"
            f"下注金额: {room.bet_amount} 金币\n"
            f"当前玩家: 1/{room.max_players}\n\n"
            f"🔹 其他玩家使用命令加入游戏\n"
            f"🔹 {room.min_players}人以上可开始游戏"
        )
    
    def _build_player_joined_message(self, room: GameRoom, username: str, can_start: bool, engine: GameEngine) -> str:
        """构建玩家加入消息"""
        message = (
            f"✅ {username} 已加入 {engine.display_name} #{room.id}！\n\n"
            f"当前玩家: {len(room.players)}/{room.max_players}\n"
        )
        
        player_list = [p['username'] for p in room.players]
        message += f"玩家列表: {', '.join(player_list)}\n\n"
        
        if can_start:
            message += f"🔹 创建者 {room.creator_name} 可以开始游戏"
        else:
            message += f"🔹 等待更多玩家加入（至少{room.min_players}人）"
        
        return message
