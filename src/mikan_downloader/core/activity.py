import logging
from ..db.models import ActivityLog

log = logging.getLogger("Activity")

async def log_activity(action: str, anime_title: str = None, episode: str = None, detail: str = None):
    """
    记录操作日志
    action: fetch / push / rename / error
    """
    try:
        await ActivityLog.create(
            action=action,
            anime_title=anime_title,
            episode=episode,
            detail=detail,
        )
    except Exception as e:
        log.error(f"写入活动日志失败: {e}")
