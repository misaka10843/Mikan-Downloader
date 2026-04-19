from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import feedparser
import re
from ..core.search import search_bangumi, get_rss_metadata
from ..core.downloader import mikan_request, check_history, add_to_history
from ..core.renamer import parse_episode_number
from ..core.config import read_config
from ..db.models import Subscription

router = APIRouter(prefix="/api/mikan", tags=["mikan"])

@router.get("/subs")
async def get_subs():
    subs = await Subscription.filter(is_deleted=False).all()
    return [
        {
            "url": s.url,
            "date": s.date,
            "rule": s.rule,
            "rename_rule": s.rename_rule,
            "is_deleted": s.is_deleted,
            "title": s.title,
            "cover": s.cover
        } for s in subs
    ]

@router.post("/subs")
async def save_subs(data: List[Dict[str, Any]]):
    await Subscription.all().update(is_deleted=True)
    for sub in data:
        await Subscription.update_or_create(
            url=sub.get("url"),
            defaults={
                "date": sub.get("date"),
                "rule": sub.get("rule"),
                "rename_rule": sub.get("rename_rule", "auto"),
                "title": sub.get("title"),
                "cover": sub.get("cover"),
                "is_deleted": False
            }
        )
    return {"status": "success", "message": "订阅已更新"}

@router.get("/search")
async def search_mikan_api(q: str):
    return await search_bangumi(q)

@router.post("/preview")
async def preview_mikan_rule(data: Dict[str, Any]):
    url = data.get("url")
    rule = data.get("rule", ".*")
    rename_rule = data.get("rename_rule", "auto")
    if not url:
        return {"status": "error", "message": "无可用源"}

    cfg = await read_config()
    api_urls = cfg.get("api_url", ["https://mikanani.me"])
    proxies = {"http": cfg['proxy'], "https": cfg['proxy']} if cfg.get('proxy') else None

    response = mikan_request(url, api_urls, True, proxies)
    if not response:
        return {"status": "error", "message": "无法获取该番剧的 RSS。"}

    feed = feedparser.parse(response.text)
    results = []
    for entry in feed.entries:
        guid = entry.id
        is_match = False
        try:
            if re.search(r'.*' + rule + '.*', guid):
                is_match = True
        except:
            is_match = False

        season, episode = parse_episode_number(guid, rename_rule)

        results.append({
            "title": guid,
            "match": is_match,
            "in_history": await check_history(guid),
            "season": season,
            "episode": episode
        })

    return {"status": "success", "results": results}

@router.get("/fetch_rss")
async def fetch_rss_info(url: str):
    return await get_rss_metadata(url)

@router.post("/history/add")
async def add_to_history_api(data: Dict[str, Any]):
    source = data.get("source")
    guids = data.get("guids", [])
    if not source:
        raise HTTPException(status_code=400, detail="Missing source")
    
    for guid in guids:
        await add_to_history(guid, source)
    
    return {"status": "success", "message": f"成功添加 {len(guids)} 条记录到历史"}
