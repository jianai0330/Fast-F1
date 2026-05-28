from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from urllib.parse import urlparse
from routers import telemetry, analysis, qualifying, laptimes, events, standings
from routers import news, forum, admin, terms, driver as driver_router
from routers import hot
from routers import curated as curated_router
from routers import chat
from db.database import init_db
import fastf1
import os
import logging

logger = logging.getLogger(__name__)

REDIRECT_ALLOWED_HOSTS = {
    "www.the-race.com",
    "the-race.com",
    "www.motorsport.com",
    "motorsport.com",
    "www.crash.net",
    "crash.net",
    "fr.f1i.com",
    "f1i.com",
}

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

app = FastAPI(title="F1 Data API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 原有路由
app.include_router(events.router,      prefix="/events",      tags=["events"])
app.include_router(qualifying.router,  prefix="/qualifying",  tags=["qualifying"])
app.include_router(laptimes.router,    prefix="/laptimes",    tags=["laptimes"])
app.include_router(telemetry.router,   prefix="/telemetry",   tags=["telemetry"])
app.include_router(analysis.router,    prefix="/analysis",    tags=["analysis"])
app.include_router(standings.router,   prefix="/standings",   tags=["standings"])

# Phase 4 新增路由
app.include_router(news.router,        prefix="/news",        tags=["news"])
app.include_router(forum.router,       prefix="/forum",       tags=["forum"])
app.include_router(admin.router,       prefix="/admin",       tags=["admin"])
app.include_router(terms.router,       prefix="/terms",       tags=["terms"])
app.include_router(driver_router.router,                       tags=["driver"])
app.include_router(hot.router,          prefix="/hot",          tags=["hot"])
app.include_router(curated_router.router,                        tags=["curated"])
app.include_router(chat.router,           prefix="/chat",        tags=["chat"])


def _auto_crawl_job():
    """定时任务：每小时爬取新闻，不自动分析（分析由用户点击触发）"""
    try:
        from services.news_crawler import crawl_all
        crawl_result = crawl_all()
        added = crawl_result.get("added", 0)
        print(f"[auto-crawl] 新增 {added} 条新闻", flush=True)
    except Exception as e:
        print(f"[auto-crawl] 失败: {e}", flush=True)


def _warmup_sessions():
    """后台预热：把服务器上已有缓存的 session 全部 load 进内存"""
    import os, threading
    from services.fastf1_service import get_session

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    year_dir = os.path.join(cache_dir, "2026")
    if not os.path.isdir(year_dir):
        return

    SESSION_TYPE_MAP = {
        "Qualifying": "Q",
        "Race":       "R",
        "Sprint":     "S",
    }

    def _load(year, round_name, stype):
        try:
            get_session(year, round_name, stype)
            print(f"[warmup] loaded {year} {round_name} {stype}", flush=True)
        except Exception as e:
            print(f"[warmup] skip {year} {round_name} {stype}: {e}", flush=True)

    threads = []
    for gp_folder in sorted(os.listdir(year_dir)):
        gp_path = os.path.join(year_dir, gp_folder)
        if not os.path.isdir(gp_path):
            continue
        # 从文件夹名提取 round name，例如 "2026-03-29_Japanese_Grand_Prix" → "Japanese Grand Prix"
        parts = gp_folder.split("_", 1)
        if len(parts) < 2:
            continue
        round_name = parts[1].replace("_", " ")
        for session_folder in os.listdir(gp_path):
            for label, stype in SESSION_TYPE_MAP.items():
                if label in session_folder:
                    t = threading.Thread(target=_load, args=(2026, round_name, stype), daemon=True)
                    threads.append(t)
                    break

    for t in threads:
        t.start()


def _warmup_api_cache():
    """后台预热：启动后立即拉取 events 和 standings，填充内存缓存"""
    import time as _time
    _time.sleep(2)  # 等服务完全就绪
    try:
        from routers.events import get_events
        get_events(2026)
        print("[warmup] events cache ready", flush=True)
    except Exception as e:
        print(f"[warmup] events failed: {e}", flush=True)
    try:
        from routers.standings import get_standings
        get_standings(2026)
        print("[warmup] standings cache ready", flush=True)
    except Exception as e:
        print(f"[warmup] standings failed: {e}", flush=True)


# 静态文件服务（放在路由注册之后，避免拦截 API 请求）
from fastapi.staticfiles import StaticFiles
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.on_event("startup")
def on_startup():
    """服务启动时初始化数据库，并启动定时爬虫"""
    init_db()

    # 后台预热：session 数据 + events/standings API 缓存
    import threading
    threading.Thread(target=_warmup_sessions, daemon=True).start()
    threading.Thread(target=_warmup_api_cache, daemon=True).start()

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        scheduler.add_job(_auto_crawl_job, "interval", hours=1, id="auto_crawl")
        scheduler.add_job(_warmup_api_cache, "interval", hours=2, id="standings_refresh")
        scheduler.start()
        app.state.scheduler = scheduler
        print("[scheduler] 定时爬虫已启动，每小时执行一次", flush=True)
    except Exception as e:
        print(f"[scheduler] 启动失败（不影响主服务）: {e}", flush=True)


@app.on_event("shutdown")
def on_shutdown():
    try:
        if hasattr(app.state, "scheduler"):
            app.state.scheduler.shutdown(wait=False)
    except Exception:
        pass


@app.get("/")
def root():
    return {"status": "ok", "message": "F1 Data API is running", "version": "1.0.0"}


@app.get("/redirect")
def redirect_url(url: str):
    """302 跳转中转，供微信 webview 使用（业务域名只需配 api.aifuwan.site）"""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in REDIRECT_ALLOWED_HOSTS:
        raise HTTPException(status_code=400, detail="redirect target not allowed")
    return RedirectResponse(url=url, status_code=302)
