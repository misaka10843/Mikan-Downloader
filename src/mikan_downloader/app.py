import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import RegisterTortoise
from .db.database import run_db_migrations
from .core.config import migrate_from_yaml
from .core.scheduler import init_scheduler, scheduler
from .api import mikan, settings, notifications, scheduler as scheduler_api, library, history

log = logging.getLogger("App")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 使用 RegisterTortoise 作为上下文管理器，这是 Tortoise 0.19+ 推荐的异步初始化方式
    # _enable_global_fallback=True 确保在不同的 Task 之间可以共享 DB 连接上下文
    async with RegisterTortoise(
        app,
        db_url="sqlite://history.db",
        modules={"models": ["src.mikan_downloader.db.models"]},
        generate_schemas=True,
        add_exception_handlers=True,
        _enable_global_fallback=True,
    ):
        # 运行数据库迁移
        await run_db_migrations()
        # 初始化配置迁移
        await migrate_from_yaml()
        # 初始化定时任务
        await init_scheduler()
        
        yield
        
    # 关闭逻辑
    if scheduler.running:
        scheduler.shutdown()

def create_app() -> FastAPI:
    app = FastAPI(title="Mikan Downloader", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(mikan.router)
    app.include_router(settings.router)
    app.include_router(notifications.router)
    app.include_router(scheduler_api.router)
    app.include_router(library.router)
    app.include_router(history.router)

    app.include_router(history.router)

    # 静态文件处理
    # 尝试寻找 spa_dist
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    spa_dist_path = os.path.join(base_path, "spa_dist")
    
    if os.path.exists(spa_dist_path):
        app.mount("/", StaticFiles(directory=spa_dist_path, html=True), name="static")
    else:
        log.warning(f"前端静态文件夹 {spa_dist_path} 不存在，界面将不可用")

    return app
