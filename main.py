import os
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# 导入核心模块
from .core.database.connection import init_database
from .core.repositories.sqlite_user_repo import SqliteUserRepository
from .core.repositories.sqlite_achievement_repo import SqliteAchievementRepository
from .core.repositories.sqlite_user_achievement_repo import SqliteUserAchievementRepository
from .core.repositories.sqlite_check_in_repo import SqliteCheckInRepository
from .core.repositories.sqlite_game_repo import SqliteGameRepository

# 导入服务
from .core.services.user_service import UserService
from .core.services.check_in_service import CheckInService
from .core.services.achievement_service import AchievementService
from .core.services.game_service import GameService

# 导入游戏引擎
from .games.russian_roulette_engine import RussianRouletteEngine


@register("dzgm", "kidWild", "金币管理系统", "1.0.0")
class CoinManagementPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 数据库路径配置
        plugin_data_dir = "data/plugin_data/astrbot_plugin_dzgm"
        os.makedirs(plugin_data_dir, exist_ok=True)
        self.db_path = os.path.join(plugin_data_dir, "dzgm.db")
        
        # 初始化数据库
        init_database(self.db_path)
        
        # 初始化仓储层
        self.user_repo = SqliteUserRepository(self.db_path)
        self.achievement_repo = SqliteAchievementRepository(self.db_path)
        self.user_achievement_repo = SqliteUserAchievementRepository(self.db_path)
        self.check_in_repo = SqliteCheckInRepository(self.db_path)
        self.game_repo = SqliteGameRepository(self.db_path)
        
        # 初始化服务层
        self.user_service = UserService(self.user_repo)
        self.check_in_service = CheckInService(self.user_service, self.check_in_repo)
        self.achievement_service = AchievementService(
            self.achievement_repo, 
            self.user_achievement_repo, 
            self.user_service,
            self.game_repo
        )
        
        # 初始化游戏服务
        self.game_service = GameService(self.game_repo, self.user_service, self.achievement_service)
        
        # 注册游戏引擎
        self.game_service.register_game_engine(RussianRouletteEngine())
        
        logger.info("dzgm插件初始化完成")

    async def initialize(self):
        """异步初始化"""
        # 初始化默认成就
        self.achievement_service.initialize_achievements()
        logger.info("成就系统初始化完成")
    
    @filter.command("注册")
    async def register_user(self, event: AstrMessageEvent):
        """用户注册"""
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        
        user, is_new_user = self.user_service.get_or_create_user(user_id, username)
        
        if is_new_user:
            # 发送欢迎消息
            welcome_message = f"🎉 欢迎新用户 {username} 加入！你已获得1000初始金币！"
            yield event.plain_result(welcome_message)
        else:
            yield event.plain_result(f"👋 {username}，你已是注册用户！")

    @filter.command("状态")
    async def show_status(self, event: AstrMessageEvent):
        """查看用户状态"""
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        
        user_info = self.user_service.get_user_info(user_id)
        
        if not user_info:
            yield event.plain_result("❌ 获取用户信息失败, 请先注册！")
            return
            
        user = user_info['user']
        rank = user_info['rank']
        
        message = (
            f"💰 {username} 的信息\n\n"
            f"当前金币: {user.coins:,}\n"
            f"等级: Lv.{user.level} (经验: {user.experience})\n"
            f"称号: {user.title}\n"
            f"排名: #{rank if rank else 'N/A'}\n"
            f"累计收入: {user.total_earned:,}\n"
            f"累计支出: {user.total_spent:,}\n"
            f"连续签到: {user.check_in_count} 天\n"
            f"总签到次数: {user.total_check_ins} 次"
        )
        
        yield event.plain_result(message)

    @filter.command("签到")
    async def check_in(self, event: AstrMessageEvent):
        """用户签到"""
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        
        result = self.check_in_service.check_in(user_id, username)
        
        if result['success']:
            if result.get('is_new_user'):
                # 发送欢迎消息
                welcome_message = f"🎉 欢迎新用户 {username} 加入！你已获得1000初始金币！"
                yield event.plain_result(welcome_message)
            message = (
                f"✅ 签到成功！\n\n"
                f"基础奖励: {result['base_reward']} 金币\n"
                f"连续奖励: {result['bonus_reward']} 金币\n"
                f"总获得: {result['total_reward']} 金币\n"
                f"连续签到: {result['consecutive_days']} 天\n"
                f"当前金币: {result['current_coins']:,}\n"
                f"总签到次数: {result['total_check_ins']} 次"
            )
            if result.get('new_title'):
                message += f"\n🎉 获得新称号: {result['new_title']}"
            
            # 检查签到相关成就
            achievements = self.achievement_service.check_and_award_achievements(
                user_id, "check_in", result['consecutive_days']
            )
            if achievements:
                message += f"\n\n🏆 获得成就: {', '.join(a.name for a in achievements)}"
        else:
            message = f"❌ {result['message']}"
        
        yield event.plain_result(message)

    @filter.command("排行榜")
    async def leaderboard(self, event: AstrMessageEvent):
        """查看排行榜"""
        args = event.message_str.split()
        limit = 10
        if len(args) > 1:
            try:
                limit = min(int(args[1]), 20)  # 最多显示20名
            except ValueError:
                pass
        
        leaderboard = self.user_service.get_leaderboard(limit)
        
        if not leaderboard:
            yield event.plain_result("📊 排行榜暂无数据")
            return
        
        message = "🏆 金币排行榜\n\n"
        for entry in leaderboard:
            medal = "🥇" if entry.rank == 1 else "🥈" if entry.rank == 2 else "🥉" if entry.rank == 3 else f"{entry.rank}."
            message += f"{medal} {entry.username} - {entry.score:,} 金币 [{entry.title}]\n"
        
        # 显示当前用户排名
        user_rank = self.user_service.get_user_rank(event.get_sender_id())
        if user_rank and user_rank > limit:
            user_info = self.user_service.get_user_info(event.get_sender_id())
            if user_info:
                user = user_info['user']
                message += f"\n---\n{user_rank}. {user.username} - {user.coins:,} 金币 [{user.title}]"
        
        yield event.plain_result(message)

    @filter.command("轮盘")
    async def russian_roulette(self, event: AstrMessageEvent):
        """俄罗斯轮盘游戏"""
        args = event.message_str.split()
        
        if len(args) < 2:
            # 获取游戏引擎并显示规则
            engine = self.game_service.game_engines.get('russian_roulette')
            if engine:
                rules = engine.get_game_rules()
                yield event.plain_result(rules)
            else:
                yield event.plain_result("❌ 俄罗斯轮盘游戏不可用")
            return
        
        action = args[1].lower()
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        
        # 获取频道ID（群聊ID或私聊ID）
        channel_id = getattr(event, 'session_id', user_id)  # 使用session_id作为频道标识
        
        if action == "创建":
            if len(args) < 3:
                yield event.plain_result("❌ 请指定下注金额\n使用方法: /轮盘 创建 <金额>")
                return
            
            try:
                bet_amount = int(args[2])
            except ValueError:
                yield event.plain_result("❌ 请输入有效的下注金额")
                return
            
            result = self.game_service.create_room('russian_roulette', channel_id, user_id, username, bet_amount)
            yield event.plain_result(result['message'])
        
        elif action == "列表":
            game_list = self.game_service.get_room_list(channel_id, 'russian_roulette')
            yield event.plain_result(game_list)
        
        elif action == "加入":
            if len(args) < 3:
                yield event.plain_result("❌ 请指定游戏ID\n使用方法: /轮盘 加入 <游戏ID>")
                return
            
            room_id = args[2]
            result = self.game_service.join_room(room_id, user_id, username)
            yield event.plain_result(result['message'])
        
        elif action == "开始":
            if len(args) < 3:
                yield event.plain_result("❌ 请指定游戏ID\n使用方法: /轮盘 开始 <游戏ID>")
                return
            
            room_id = args[2]
            result = self.game_service.start_room(room_id, user_id)
            yield event.plain_result(result['message'])
        
        elif action == "开枪":
            shots = 1
            if len(args) >= 3:
                try:
                    shots = int(args[2])
                except ValueError:
                    yield event.plain_result("❌ 请输入有效的开枪数量（1-3）")
                    return
            
            # 查找用户当前参与的游戏
            user_rooms = self.game_service.game_repo.get_user_rooms(user_id, 'playing')
            roulette_rooms = [r for r in user_rooms if r.game_type == 'russian_roulette' and r.channel_id == channel_id]
            
            if not roulette_rooms:
                yield event.plain_result("❌ 当前没有进行中的轮盘游戏")
                return
            
            room = roulette_rooms[0]
            result = self.game_service.process_game_action(room.id, user_id, 'shoot', {'shots': shots})
            yield event.plain_result(result['message'])
        
        elif action == "取消":
            if len(args) < 3:
                yield event.plain_result("❌ 请指定游戏ID\n使用方法: /轮盘 取消 <游戏ID>")
                return
            
            room_id = args[2]
            result = self.game_service.cancel_room(room_id, user_id)
            yield event.plain_result(result['message'])
        
        else:
            # 兼容旧的直接下注方式，显示帮助
            help_text = (
                "🎲 多人俄罗斯轮盘游戏\n\n"
                "可用命令:\n"
                "• /轮盘 - 查看游戏规则\n"
                "• /轮盘 创建 <金额> - 创建游戏房间\n"
                "• /轮盘 列表 - 查看当前游戏\n"
                "• /轮盘 加入 <游戏ID> - 加入游戏\n"
                "• /轮盘 开始 <游戏ID> - 开始游戏\n"
                "• /轮盘 开枪 [枪数] - 开枪（1-3枪）\n"
                "• /轮盘 取消 <游戏ID> - 取消游戏\n"
                "• /轮盘统计 - 查看个人统计"
            )
            yield event.plain_result(help_text)

    @filter.command("轮盘统计")
    async def roulette_stats(self, event: AstrMessageEvent):
        """查看轮盘游戏统计"""
        user_id = event.get_sender_id()
        
        # 从游戏记录表中获取统计数据
        records = self.game_repo.get_user_game_records(user_id, "russian_roulette", limit=1000)
        
        if not records:
            yield event.plain_result("📊 你还没有轮盘游戏记录哦！\n使用 /轮盘 创建 开始游戏")
            return
        
        total_games = len(records)
        wins = sum(1 for r in records if r.result == "win")
        losses = total_games - wins
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        total_bet = sum(r.coins_bet for r in records)
        total_won = sum(r.coins_won for r in records)
        total_earnings = total_won - total_bet
        avg_profit = total_earnings / total_games if total_games > 0 else 0
        
        max_win = max(r.coins_won for r in records) if records else 0
        worst_loss = max(r.coins_bet for r in records if r.result != "win") if records else 0
        
        message = (
            f"🎲 {event.get_sender_name()} 的轮盘统计\n\n"
            f"总游戏次数: {total_games}\n"
            f"胜利次数: {wins}\n"
            f"失败次数: {losses}\n"
            f"胜率: {win_rate:.1f}%\n"
            f"总下注: {total_bet:,} 金币\n"
            f"总赢得: {total_won:,} 金币\n"
            f"净收益: {total_earnings:,} 金币\n"
            f"平均收益: {avg_profit:.1f} 金币\n"
            f"最大单次赢得: {max_win:,} 金币\n"
            f"最差单次损失: {worst_loss:,} 金币"
        )
        
        yield event.plain_result(message)

    @filter.command("成就")
    async def achievements(self, event: AstrMessageEvent):
        """查看成就"""
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        
        # 确保用户存在
        user = self.user_service.get_user_info(user_id)
        if not user:
            yield event.plain_result("❌ 获取用户信息失败, 请先注册！")
            return

        progress = self.achievement_service.get_achievement_progress(user_id)
        
        if not progress:
            yield event.plain_result("📊 成就系统暂无数据")
            return
        
        message = f"🏆 {username} 的成就进度\n\n"
        message += f"总进度: {progress['completed_achievements']}/{progress['total_achievements']} "
        message += f"({progress['completion_rate'] * 100:.1f}%)\n\n"
        
        for category, data in progress['categories'].items():
            if data['total'] == 0:
                continue
            
            message += f"📋 {category} ({data['completed']}/{data['total']})\n"
            
            # 显示前几个成就的进度
            for ach_data in data['achievements'][:3]:
                achievement = ach_data['achievement']
                if ach_data['completed']:
                    message += f"✅ {achievement.name}\n"
                else:
                    progress_rate = ach_data['progress_rate'] * 100
                    message += f"⏳ {achievement.name} ({progress_rate:.1f}%)\n"
            
            if len(data['achievements']) > 3:
                message += f"   ... 还有 {len(data['achievements']) - 3} 个成就\n"
            message += "\n"
        
        # 检查是否有新成就
        new_achievements = self.achievement_service.get_unnotified_achievements(user_id)
        if new_achievements:
            message += "🎉 新获得的成就:\n"
            for achievement in new_achievements:
                message += f"🏆 {achievement.name} - {achievement.description}\n"
                if achievement.reward_coins > 0:
                    message += f"   奖励: {achievement.reward_coins} 金币\n"
                if achievement.reward_title:
                    message += f"   称号: {achievement.reward_title}\n"
        
        yield event.plain_result(message)

    @filter.command("转账")
    async def transfer_coins(self, event: AstrMessageEvent):
        """转账金币"""
        args = event.message_str.split()
        
        if len(args) < 3:
            yield event.plain_result("💸 转账使用方法: /转账 @用户 <金额>\n例如: /转账 @张三 100")
            return
        
        try:
            amount = int(args[2])
        except ValueError:
            yield event.plain_result("❌ 请输入有效的转账金额")
            return
        
        if amount <= 0:
            yield event.plain_result("❌ 转账金额必须大于0")
            return
        
        # 获取目标用户（这里需要根据实际情况解析@用户）
        # 简化实现，假设args[1]是用户ID
        target_user_input = args[1].strip('@')
        
        # 这里需要根据实际bot框架的用户解析方式来实现
        # 暂时使用简化版本
        yield event.plain_result("🚧 转账功能开发中，敬请期待！")

    @filter.command("游戏")
    async def game_management(self, event: AstrMessageEvent):
        """游戏管理命令"""
        args = event.message_str.split()
        
        if len(args) < 2:
            # 显示可用游戏列表
            available_games = self.game_service.get_available_games()
            if not available_games:
                yield event.plain_result("❌ 当前没有可用的游戏")
                return
            
            message = "🎮 可用游戏列表\n\n"
            for game_info in available_games:
                message += f"🎯 {game_info['name']} ({game_info['type']})\n"
                message += f"   玩家数: {game_info['min_players']}-{game_info['max_players']}人\n"
                message += f"   下注范围: {game_info['min_bet']}-{game_info['max_bet']} 金币\n\n"
            
            message += "使用方法: /游戏 <游戏类型> <操作> [参数]\n"
            message += "例如: /游戏 轮盘 创建 500"
            
            yield event.plain_result(message)
            return
        
        action = args[1].lower()
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        channel_id = getattr(event, 'session_id', user_id)
        
        if action == "列表":
            # 显示当前频道的所有游戏房间
            room_list = self.game_service.get_room_list(channel_id)
            yield event.plain_result(room_list)
        
        elif action == "我的":
            # 显示用户参与的游戏房间
            user_rooms = self.game_service.game_repo.get_user_rooms(user_id)
            if not user_rooms:
                yield event.plain_result("📋 你当前没有参与任何游戏")
                return
            
            message = "🎮 你参与的游戏\n\n"
            for room in user_rooms:
                engine = self.game_service.game_engines.get(room.game_type)
                if engine:
                    status_emoji = {"waiting": "⏳", "playing": "🔥", "finished": "✅", "cancelled": "❌"}
                    message += f"{status_emoji.get(room.status, '🎮')} {engine.display_name} #{room.id}\n"
                    message += f"   状态: {room.status}\n"
                    message += f"   下注: {room.bet_amount} 金币\n"
                    if room.status == 'playing':
                        message += f"   {engine.get_game_status(room)}\n"
                    message += "\n"
            
            yield event.plain_result(message)
        
        else:
            yield event.plain_result("❌ 无效的游戏命令\n使用 /游戏 查看帮助")

    @filter.command("帮助")
    async def help_coins(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = (
            "💰 金币管理系统帮助\n\n"
            "基础命令:\n"
            "• /金币 - 查看金币信息\n"
            "• /签到 - 每日签到获得金币\n"
            "• /排行榜 [数量] - 查看金币排行榜\n"
            "• /成就 - 查看成就进度\n\n"
            "游戏命令:\n"
            "• /轮盘 <金额> - 俄罗斯轮盘游戏\n"
            "• /轮盘统计 - 查看游戏统计\n\n"
            "其他命令:\n"
            "• /转账 @用户 <金额> - 转账金币(开发中)\n"
            "• /金币帮助 - 显示此帮助信息\n\n"
            "🎯 每日签到可获得随机金币奖励\n"
            "🏆 完成各种成就可获得丰厚奖励\n"
            "🎲 参与游戏有机会赢得大量金币"
        )
        
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件销毁方法"""
        logger.info("金币管理系统插件已卸载")
