-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    coins INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    check_in_count INTEGER DEFAULT 0,
    last_check_in TIMESTAMP NULL,
    total_check_ins INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    experience INTEGER DEFAULT 0,
    title TEXT DEFAULT '新人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建成就表
CREATE TABLE IF NOT EXISTS achievements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    condition_type TEXT NOT NULL,
    condition_value INTEGER NOT NULL,
    reward_coins INTEGER DEFAULT 0,
    reward_title TEXT NULL,
    icon TEXT NULL,
    is_hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建用户成就关联表
CREATE TABLE IF NOT EXISTS user_achievements (
    user_id TEXT,
    achievement_id TEXT,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (achievement_id) REFERENCES achievements(id)
);

-- 创建签到记录表
CREATE TABLE IF NOT EXISTS check_in_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    check_in_date DATE NOT NULL,
    coins_earned INTEGER NOT NULL,
    consecutive_days INTEGER NOT NULL,
    bonus_coins INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, check_in_date)
);

-- 创建游戏记录表
CREATE TABLE IF NOT EXISTS game_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    game_type TEXT NOT NULL,
    coins_bet INTEGER DEFAULT 0,
    coins_won INTEGER DEFAULT 0,
    result TEXT NOT NULL,
    details TEXT NULL, -- JSON格式的详细信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_coins ON users(coins DESC);
CREATE INDEX IF NOT EXISTS idx_users_level ON users(level DESC);
CREATE INDEX IF NOT EXISTS idx_check_in_records_user_date ON check_in_records(user_id, check_in_date);
CREATE INDEX IF NOT EXISTS idx_game_records_user_type ON game_records(user_id, game_type);
CREATE INDEX IF NOT EXISTS idx_game_records_created_at ON game_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_category ON achievements(category);
