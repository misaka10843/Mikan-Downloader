from fastapi import APIRouter, Query
from ..db.models import ActivityLog

router = APIRouter(prefix="/api/activity", tags=["activity"])

@router.get("/logs")
async def get_activity_logs(
    limit: int = 100,
    offset: int = 0,
    action: str = Query(None),
):
    query = ActivityLog.all()
    if action:
        query = query.filter(action=action)
    total = await query.count()
    items = await query.order_by("-timestamp").limit(limit).offset(offset).all()
    return {
        "total": total,
        "items": [
            {
                "id": i.id,
                "action": i.action,
                "anime_title": i.anime_title,
                "episode": i.episode,
                "detail": i.detail,
                "timestamp": i.timestamp.strftime("%Y-%m-%d %H:%M:%S") if i.timestamp else None,
            }
            for i in items
        ],
    }

@router.delete("/logs")
async def clear_activity_logs():
    await ActivityLog.all().delete()
    return {"status": "success"}
