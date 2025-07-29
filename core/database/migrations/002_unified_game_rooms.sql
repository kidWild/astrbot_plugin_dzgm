-- 002: 添加通用游戏房间表，替换轮盘游戏专用表
-- 创建通用游戏房间表
CREATE TABLE IF NOT EXISTS game_rooms (
    id TEXT PRIMARY KEY,
    game_type TEXT NOT NULL,  -- 游戏类型：russian_roulette, blackjack, poker等
    channel_id TEXT NOT NULL,  -- 群聊ID或私聊ID
    creator_id TEXT NOT NULL,  -- 创建者ID
    creator_name TEXT NOT NULL,  -- 创建者名称
    bet_amount INTEGER NOT NULL,  -- 下注金额
    status TEXT NOT NULL DEFAULT 'waiting',  -- 游戏状态：waiting, playing, finished, cancelled
    max_players INTEGER NOT NULL DEFAULT 6,  -- 最大玩家数
    min_players INTEGER NOT NULL DEFAULT 2,  -- 最小玩家数
    players TEXT NOT NULL DEFAULT '[]',  -- 参与玩家JSON
    game_data TEXT DEFAULT '{}',  -- 游戏特定数据JSON
    settings TEXT DEFAULT '{}',  -- 游戏设置JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_game_rooms_channel_status ON game_rooms(channel_id, status);
CREATE INDEX IF NOT EXISTS idx_game_rooms_creator ON game_rooms(creator_id);
CREATE INDEX IF NOT EXISTS idx_game_rooms_type_status ON game_rooms(game_type, status);

-- 迁移现有轮盘游戏数据到新表
INSERT INTO game_rooms (
    id, game_type, channel_id, creator_id, creator_name, bet_amount, 
    status, max_players, min_players, players, game_data, settings,
    created_at, started_at, finished_at
)
SELECT 
    id,
    'russian_roulette' as game_type,
    channel_id,
    creator_id,
    creator_name,
    bet_amount,
    status,
    max_players,
    2 as min_players,
    players,
    json_object(
        'bullet_position', bullet_position,
        'current_position', current_position,
        'current_player_index', current_player_index
    ) as game_data,
    '{}' as settings,
    created_at,
    started_at,
    finished_at
FROM roulette_games WHERE EXISTS (SELECT 1 FROM roulette_games);

-- 删除旧的轮盘游戏表
DROP TABLE IF EXISTS roulette_games;
