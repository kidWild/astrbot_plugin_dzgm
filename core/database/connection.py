import sqlite3
import os
from typing import List
from astrbot.api import logger


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问
    return conn


def execute_sql_file(conn: sqlite3.Connection, sql_file_path: str) -> None:
    """执行SQL文件"""
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 分割SQL语句并执行
    statements = sql_content.split(';')
    for statement in statements:
        statement = statement.strip()
        if statement:
            conn.execute(statement)


def run_migrations(db_path: str, migrations_dir: str) -> None:
    """运行数据库迁移"""
    conn = get_db_connection(db_path)
    
    try:
        # 创建迁移记录表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 获取已应用的迁移
        cursor = conn.execute('SELECT version FROM schema_migrations')
        applied_migrations = {row[0] for row in cursor.fetchall()}
        
        # 获取所有迁移文件
        if not os.path.exists(migrations_dir):
            logger.info(f"迁移目录不存在: {migrations_dir}")
            return
            
        migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.sql')]
        migration_files.sort()
        
        # 应用未执行的迁移
        for migration_file in migration_files:
            version = migration_file[:-4]  # 移除.sql后缀
            
            if version not in applied_migrations:
                logger.info(f"应用迁移: {version}")
                migration_path = os.path.join(migrations_dir, migration_file)
                
                try:
                    execute_sql_file(conn, migration_path)
                    conn.execute('INSERT INTO schema_migrations (version) VALUES (?)', (version,))
                    conn.commit()
                    logger.info(f"迁移 {version} 应用成功")
                except Exception as e:
                    logger.error(f"迁移 {version} 应用失败: {e}")
                    conn.rollback()
                    raise
        
    finally:
        conn.close()


def init_database(db_path: str) -> None:
    """初始化数据库"""
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    run_migrations(db_path, migrations_dir)
