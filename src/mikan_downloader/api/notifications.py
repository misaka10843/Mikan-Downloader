from fastapi import APIRouter
from typing import Dict, Any
from ..core.notifications import get_notifications, mark_read, clear_notifications

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
async def get_notifications_api(limit: int = 50, unread: bool = False):
    return await get_notifications(limit, unread)

@router.post("/read")
async def read_notifications_api(data: Dict[str, Any]):
    ids = data.get("ids")
    await mark_read(ids)
    return {"status": "success"}

@router.delete("")
async def clear_notifications_api():
    await clear_notifications()
    return {"status": "success"}
