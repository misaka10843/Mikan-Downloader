from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import requests
import time
from ..core.config import read_config, save_config

router = APIRouter(prefix="/api", tags=["settings"])

@router.post("/settings/test_url")
async def test_url_latency(data: Dict[str, str]):
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    
    start_time = time.time()
    try:
        cfg = await read_config()
        proxies = {"http": cfg['proxy'], "https": cfg['proxy']} if cfg.get('proxy') else None
        
        # 使用 HEAD 请求测试，超时 5 秒
        response = requests.head(url, timeout=5, proxies=proxies)
        duration = int((time.time() - start_time) * 1000)
        return {
            "status": "success",
            "latency": duration,
            "code": response.status_code
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/config")
async def get_settings():
    return await read_config()

@router.post("/config")
async def update_settings(config_data: Dict[str, Any]):
    if await save_config(config_data):
        return {"status": "success", "message": "配置保存成功"}
    raise HTTPException(status_code=500, detail="保存配置失败")

@router.get("/settings/system")
async def get_system():
    cfg = await read_config()
    return {
        "proxy": cfg.get("proxy", ""),
        "api_url": cfg.get("api_url", ["https://mikanani.me"]),
        "save_dir": cfg.get("save_dir", ""),
        "torrent_dir": cfg.get("torrent_dir", ""),
        "aria2": cfg.get("aria2", {"host": "", "port": 6800, "secret": ""}),
        "schedule": cfg.get("schedule", {"mode": "cron", "cron_time": "00:00", "interval": 15})
    }

@router.post("/settings/system")
async def save_system(data: Dict[str, Any]):
    # 直接将前端发送的系统配置项保存到数据库
    # 这会覆盖所有的顶层配置键 (proxy, api_url, save_dir, aria2, schedule 等)
    if await save_config(data):
        return {"status": "success", "message": "系统设置已更新"}
    raise HTTPException(status_code=500, detail="保存设置失败")
