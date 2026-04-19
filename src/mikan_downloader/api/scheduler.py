from fastapi import APIRouter
from ..core.scheduler import scheduler, restart_scheduler
from ..core.downloader import run_download_task
from ..db.models import TaskLog

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

@router.post("/update")
async def update_schedule(body: dict):
    await restart_scheduler()
    return {"status": "success"}

@router.post("/run")
async def trigger_run():
    # 触发一次异步调度任务
    scheduler.add_job(run_download_task, id="manual_trigger_run")
    return {"status": "success", "message": "任务已在后台启动"}

@router.get("/jobs")
async def get_jobs():
    jobs = []
    # 获取所有的执行日志
    logs = await TaskLog.all()
    log_map = {l.job_id: l for l in logs}

    for job in scheduler.get_jobs():
        task_log = log_map.get(job.id)
        jobs.append({
            "id": job.id,
            "next_run_time": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "已暂停或未知",
            "last_run_time": task_log.last_run.strftime("%Y-%m-%d %H:%M:%S") if task_log and task_log.last_run else "未知 / 刚启动",
            "status": task_log.status if task_log else "unknown",
            "message": task_log.message if task_log else "",
            "name": job.name
        })
    return {"status": "success", "jobs": jobs}
