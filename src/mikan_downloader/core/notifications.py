from ..db.models import Notification

async def add_notification(level: str, title: str, message: str):
    """
    添加新通知 (异步 ORM 版)
    level: info, success, warning, error
    """
    try:
        await Notification.create(level=level, title=title, message=message)
    except Exception as e:
        import logging
        logging.getLogger("Notifications").error(f"Failed to add notification: {e}")

async def get_notifications(limit=50, unread_only=False):
    """
    获取通知列表
    """
    query = Notification.all().order_by("-timestamp")
    if unread_only:
        query = query.filter(is_read=False)
    
    # 使用 values() 转换成原始字典列表，方便 API 返回
    items = await query.limit(limit).values()
    
    # 格式化时间戳为字符串，保持与前端兼容
    for item in items:
        if item.get("timestamp"):
            item["timestamp"] = item["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            
    return items

async def mark_read(ids=None):
    """
    标记已读
    """
    if ids is None:
        await Notification.all().update(is_read=True)
    else:
        # 兼容单 ID 和 ID 列表
        target_ids = [ids] if isinstance(ids, int) else ids
        await Notification.filter(id__in=target_ids).update(is_read=True)

async def clear_notifications():
    """
    清空所有通知
    """
    await Notification.all().delete()
