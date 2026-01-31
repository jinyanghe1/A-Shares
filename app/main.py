"""FastAPI 主应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import os

from app.config import settings
from app.routers import stocks, alerts
from app.routers.analysis import router as analysis_router
from app.services.stock_service import stock_service
from app.services.alert_service import alert_service
from app.services.deepseek_service import deepseek_service
from app.utils.eastmoney import eastmoney_api

# 定时任务调度器
scheduler = AsyncIOScheduler()


async def scheduled_check_alerts():
    """
    定时检查提醒
    """
    try:
        quotes = await stock_service.get_watch_list_quotes()
        watch_list = {item.code: item for item in stock_service.get_watch_list()}

        for quote in quotes:
            code = quote["code"]
            watch_item = watch_list.get(code)

            triggered_alerts = alert_service.check_alerts(
                code=code,
                name=quote.get("name", ""),
                price=quote.get("price", 0),
                change_percent=quote.get("change_percent", 0),
                alert_up=watch_item.alert_up if watch_item else None,
                alert_down=watch_item.alert_down if watch_item else None
            )

            for alert in triggered_alerts:
                alert_service.mark_alert_sent(alert)
                print(f"[提醒] {alert.message}")

    except Exception as e:
        print(f"定时检查提醒出错: {e}")


async def scheduled_refresh_quotes():
    """
    定时刷新行情数据
    """
    try:
        quotes = await stock_service.get_watch_list_quotes()
        if quotes:
            print(f"[刷新] 已更新 {len(quotes)} 只股票行情")
    except Exception as e:
        print(f"定时刷新行情出错: {e}")


async def scheduled_save_snapshot():
    """
    定时保存行情快照（每小时）
    """
    try:
        await stock_service.save_daily_snapshot()
    except Exception as e:
        print(f"定时保存快照出错: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"启动 {settings.app_name}...")
    print(f"访问 http://localhost:8000 查看前端界面")

    # 启动定时任务
    scheduler.add_job(
        scheduled_check_alerts,
        IntervalTrigger(seconds=settings.refresh_interval),
        id="check_alerts",
        name="检查提醒"
    )
    scheduler.add_job(
        scheduled_refresh_quotes,
        IntervalTrigger(seconds=30),  # 每30秒刷新一次行情
        id="refresh_quotes",
        name="刷新行情数据"
    )
    scheduler.add_job(
        scheduled_save_snapshot,
        IntervalTrigger(seconds=3600),  # 每小时保存一次快照
        id="save_snapshot",
        name="保存行情快照"
    )
    scheduler.start()
    print("定时任务已启动")

    yield

    # 关闭时
    print("关闭应用...")
    scheduler.shutdown()
    await eastmoney_api.close()
    await deepseek_service.close()


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="股票盯盘、看盘系统 - 支持 AI 分析",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(stocks.router)
app.include_router(alerts.router)
app.include_router(analysis_router)

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@app.get("/", tags=["前端"], include_in_schema=False)
async def serve_frontend():
    """
    返回前端页面
    """
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health", tags=["默认"])
async def health_check():
    """
    健康检查
    """
    deepseek_configured = bool(settings.deepseek_api_key)

    return {
        "status": "healthy",
        "deepseek_configured": deepseek_configured,
        "watch_list_count": len(stock_service.get_watch_list())
    }


@app.get("/api", tags=["默认"])
async def api_info():
    """
    API 信息
    """
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "features": [
            "股票行情监控",
            "涨跌幅提醒",
            "AI 新闻/公告解读",
            "市场情绪分析"
        ]
    }


# 挂载静态文件（放在最后，避免覆盖 API 路由）
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
