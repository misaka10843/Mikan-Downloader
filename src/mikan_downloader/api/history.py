from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from ..db.models import DownloadHistory, Subscription
from ..core.downloader import remove_unknown_rss_links
from ..core.config import read_config

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/list")
async def list_history(
    q: str = Query(None), 
    limit: int = 100, 
    offset: int = 0
):
    query = DownloadHistory.all()
    if q:
        query = query.filter(guid__icontains=q)
    
    total = await query.count()
    items = await query.order_by("-created_at").limit(limit).offset(offset).all()
    
    return {
        "total": total,
        "items": [
            {
                "guid": i.guid,
                "source": i.source,
                "created_at": i.created_at.isoformat() if hasattr(i.created_at, "isoformat") else str(i.created_at) if i.created_at else None
            } for i in items
        ]
    }

@router.delete("/{guid}")
async def delete_history(guid: str):
    item = await DownloadHistory.get_or_none(guid=guid)
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    await item.delete()
    return {"status": "success"}

@router.post("/clean_orphans")
async def clean_orphans():
    config = await read_config()
    await remove_unknown_rss_links(config)
    return {"status": "success", "message": "已清理所有冗余历史记录"}
