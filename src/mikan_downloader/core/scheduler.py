import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from .downloader import run_download_task
from .renamer import process_completed_downloads
from .config import read_config
from ..db.models import TaskLog

log = logging.getLogger("Scheduler")
scheduler = AsyncIOScheduler()

async def job_listener(event):
    job = scheduler.get_job(event.job_id)
    if not job:
        return
    
    status = "success" if event.code == EVENT_JOB_EXECUTED else "error"
    message = str(event.exception) if event.code == EVENT_JOB_ERROR else "执行完成"
    
    await TaskLog.update_or_create(
        job_id=event.job_id,
        defaults={
            "last_run": datetime.datetime.now(),
            "status": status,
            "message": message
        }
    )

async def init_scheduler():
    log.info("初始化后台定时任务 (Async 版)...")
    
    # 注册监听器
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    cfg = await read_config()
    schedule_cfg = cfg.get("schedule", {})
    mode = schedule_cfg.get("mode", "cron")
    
    if mode == "cron_advanced":
        from apscheduler.triggers.cron import CronTrigger
        cron_expr = schedule_cfg.get("cron", "30 2 * * *")
        trigger = CronTrigger.from_crontab(cron_expr)
        log.info(f"RSS 订阅检查任务配置为高级 Cron: {cron_expr}")
    elif mode == "cron":
        time_str = schedule_cfg.get("cron_time", "00:00")
        parts = time_str.split(":")
        hour = int(parts[0]) if len(parts) == 2 else 0
        minute = int(parts[1]) if len(parts) == 2 else 0
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger(hour=hour, minute=minute)
        log.info(f"RSS 订阅检查任务配置为: 每天 {hour:02d}:{minute:02d}")
    else:
        interval = int(schedule_cfg.get("interval", 15))
        trigger = IntervalTrigger(minutes=interval)
        log.info(f"RSS 订阅检查任务配置为: 每隔 {interval} 分钟")

    # 注意：AsyncIOScheduler 会自动处理协程函数
    scheduler.add_job(
        run_download_task,
        trigger,
        id="mikan_download_task",
        replace_existing=True
    )
    
    # 每隔 5 分钟检查一次 Aria2 完成状态并重命名
    scheduler.add_job(
        process_completed_downloads,
        IntervalTrigger(minutes=5),
        id="mikan_renamer_task",
        replace_existing=True
    )
    
    if not scheduler.running:
        scheduler.start()
        
    # 启动时立刻异步执行一次
    scheduler.add_job(run_download_task, id="run_once_downloader")
    scheduler.add_job(process_completed_downloads, id="run_once_renamer")

async def restart_scheduler():
    log.info("重启定时任务...")
    if scheduler.running:
        scheduler.shutdown()
    await init_scheduler()
