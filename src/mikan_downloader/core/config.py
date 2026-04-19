import logging
import os
import yaml
import json
from ..db.models import SystemConfig, Subscription

log = logging.getLogger("Config")
CONFIG_PATH = 'config.yml'

async def get_system_settings():
    """获取所有系统设置"""
    configs = await SystemConfig.all()
    # 转换为 dict，默认值处理
    settings = {}
    for c in configs:
        if c.value is None:
            settings[c.key] = None
            continue
            
        try:
            settings[c.key] = json.loads(c.value)
        except:
            # 针对可能存在的历史原始字符串数据进行回退
            settings[c.key] = c.value
    
    # 设置默认值，防止数据库没有任何内容时出错
    defaults = {
        "proxy": "",
        "api_url": ["https://mikanani.me"],
        "save_dir": "",
        "torrent_dir": "",
        "aria2": {"host": "http://127.0.0.1", "port": 6800, "secret": ""},
        "schedule": {"mode": "cron", "cron_time": "00:00", "interval": 15}
    }
    
    for k, v in defaults.items():
        if k not in settings:
            settings[k] = v
            
    return settings

async def get_subscriptions():
    """获取所有订阅"""
    return await Subscription.filter(is_deleted=False).all()

async def read_config():
    """
    提供给各个模块使用的聚合配置读取 (异步版)
    返回格式尽量保持与原 YAML 一致，方便最小化改动
    """
    settings = await get_system_settings()
    subs = await Subscription.all()
    
    # 格式化订阅列表，排除掉 mark 为 deleted 的项目（如果逻辑需要）
    mikan_list = []
    for s in subs:
        mikan_list.append({
            "url": s.url,
            "rule": s.rule,
            "rename_rule": s.rename_rule,
            "date": s.date,
            "title": s.title,
            "cover": s.cover,
            "is_deleted": s.is_deleted
        })
    
    settings["mikan"] = mikan_list
    return settings

async def save_config(config_data):
    """
    将全量配置保存到数据库 (异步版)
    """
    try:
        # 1. 保存系统设置
        for k, v in config_data.items():
            if k == "mikan":
                continue
            
            # 使用 json.dumps 确保所有类型都以合法的 JSON 格式保存 (包括带引号的字符串)
            val_str = json.dumps(v, ensure_ascii=False)
                
            await SystemConfig.update_or_create(key=k, defaults={'value': val_str})
            
        # 2. 保存订阅 (全量更新逻辑：通常前端会发全量，我们简单处理为更新或新增)
        # 注意：这里的逻辑取决于前端是发增量还是全量。
        # 原 save_config 是覆盖文件，所以这里我们也认为是某种形式的同步。
        if "mikan" in config_data:
            for sub_data in config_data["mikan"]:
                url = sub_data.get("url")
                if not url: continue
                await Subscription.update_or_create(
                    url=url,
                    defaults={
                        "rule": sub_data.get("rule", ".*"),
                        "rename_rule": sub_data.get("rename_rule", "auto"),
                        "date": sub_data.get("date"),
                        "title": sub_data.get("title"),
                        "cover": sub_data.get("cover"),
                        "is_deleted": sub_data.get("is_deleted", False)
                    }
                )
        return True
    except Exception as e:
        log.error(f"保存配置到数据库出错: {e}")
        return False

async def migrate_from_yaml():
    """
    从 YAML 迁移到数据库。如果数据库 SystemConfig 为空且 YAML 存在则执行。
    """
    if await SystemConfig.exists():
        return
    
    if not os.path.exists(CONFIG_PATH):
        log.info("未检测到 config.yml，跳过迁移。")
        return
        
    log.info("发现 config.yml，正在迁移配置到数据库...")
    try:
        with open(CONFIG_PATH, 'r', encoding="UTF-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return
            
        await save_config(data)
        log.info("配置迁移完成。")
        
        # 备份并重命名原文件，防止重复迁移
        os.rename(CONFIG_PATH, f"{CONFIG_PATH}.bak")
        log.info(f"已将旧配置文件重命名为 {CONFIG_PATH}.bak")
    except Exception as e:
        log.error(f"迁移配置失败: {e}")
