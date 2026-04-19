from tortoise import Tortoise

async def run_db_migrations():
    """
    手动迁移：为现有的 guids 表添加 created_at 字段 (针对已存在的 SQLite 数据库)
    """
    try:
        # 确保 Tortoise 已初始化
        conn = Tortoise.get_connection("default")
        # 检查 created_at 是否已存在
        await conn.execute_query("SELECT created_at FROM guids LIMIT 1")
    except Exception:
        # 如果报错，说明字段不存在，进行添加
        from logging import getLogger
        log = getLogger("Database")
        log.info("正在为 guids 表添加 created_at 字段...")
        try:
            await conn.execute_script("ALTER TABLE guids ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            log.info("字段添加成功")
        except Exception as e:
            log.error(f"字段添加失败: {e}")
