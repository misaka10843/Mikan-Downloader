import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import read_config, save_config
from core.scheduler import init_scheduler, scheduler
from core.downloader import run_download_task

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("WebServer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/config")
def get_settings():
    return read_config()


@app.post("/api/config")
def update_settings(config_data: Dict[str, Any]):
    if save_config(config_data):
        return {"status": "success", "message": "配置保存成功"}
    raise HTTPException(status_code=500, detail="保存配置失败")


@app.get("/api/settings/system")
def get_system():
    cfg = read_config()
    return {
        "proxy": cfg.get("proxy", ""),
        "api_url": cfg.get("api_url", ["https://mikanani.me"]),
        "save_dir": cfg.get("save_dir", ""),
        "torrent_dir": cfg.get("torrent_dir", ""),
        "aria2": cfg.get("aria2", {"host": "", "port": 6800, "secret": ""}),
        "schedule": cfg.get("schedule", {"mode": "cron", "cron_time": "00:00", "interval": 15})
    }


@app.post("/api/settings/system")
def save_system(data: Dict[str, Any]):
    cfg = read_config()
    cfg["proxy"] = data.get("proxy", "")
    cfg["api_url"] = data.get("api_url", [])
    cfg["save_dir"] = data.get("save_dir", "")
    cfg["torrent_dir"] = data.get("torrent_dir", "")
    cfg["aria2"] = data.get("aria2", {})
    cfg["schedule"] = data.get("schedule", {"mode": "cron", "cron_time": "00:00", "interval": 15})
    save_config(cfg)
    return {"status": "success", "message": "系统设置已更新"}


@app.get("/api/mikan/subs")
def get_subs():
    return read_config().get("mikan", [])


@app.post("/api/mikan/subs")
def save_subs(data: List[Dict[str, Any]]):
    cfg = read_config()
    cfg["mikan"] = data
    save_config(cfg)
    return {"status": "success", "message": "订阅已更新"}


@app.get("/api/mikan/search")
def search_mikan_api(q: str):
    from core.mikan_search import search_bangumi
    return search_bangumi(q)


@app.post("/api/mikan/preview")
def preview_mikan_rule(data: Dict[str, Any]):
    import feedparser
    import re
    from core.downloader import mikan_request

    url = data.get("url")
    rule = data.get("rule", ".*")
    if not url:
        return {"status": "error", "message": "无可用源"}

    cfg = read_config()
    api_urls = cfg.get("api_url", ["https://mikanani.me"])
    proxies = {"http": cfg['proxy'], "https": cfg['proxy']} if cfg.get('proxy') else None

    response = mikan_request(url, api_urls, True, proxies)
    if not response:
        return {"status": "error", "message": "无法获取该番剧的 RSS。"}

    feed = feedparser.parse(response.text)

    results = []
    # Test items
    for entry in feed.entries:
        guid = entry.id
        is_match = False
        try:
            if re.search(r'.*' + rule + '.*', guid):
                is_match = True
        except:
            is_match = False

        results.append({
            "title": guid,
            "match": is_match
        })

    return {"status": "success", "results": results}


from core.scheduler import restart_scheduler


@app.post("/api/schedule/update")
def update_schedule(body: dict):
    restart_scheduler()
    return {"status": "success"}


@app.post("/api/run")
def trigger_run():
    from core.scheduler import scheduler, run_download_task
    scheduler.add_job(run_download_task)
    return {"status": "success", "message": "任务已在后台启动"}


@app.get("/api/schedule/jobs")
def get_jobs():
    from core.scheduler import scheduler
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run_time": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "已暂停或未知",
            "name": job.name
        })
    return {"status": "success", "jobs": jobs}


from core.fs import router as fs_router

app.include_router(fs_router)

spa_dist_path = os.path.join(os.path.dirname(__file__), "spa_dist")
if os.path.exists(spa_dist_path):
    app.mount("/", StaticFiles(directory=spa_dist_path, html=True), name="static")
else:
    log.warning(f"前端静态文件夹 {spa_dist_path} 不存在，界面将不可用")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
