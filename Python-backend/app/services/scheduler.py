"""
定时任务调度器
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("services.scheduler")

# 任务运行状态
_running = False
_task = None


async def _analysis_job():
    """学习分析定时任务"""
    from app.services.learning_analyzer import run_analysis_for_all_users
    from app.services.db.java_client import java_client

    logger.info("[定时任务] 开始学习行为分析")

    try:
        # 清理过期策略
        java_client._request("POST", "/api/tracker/internal/clean-expired")
    except Exception as e:
        logger.warning(f"[定时任务] 清理过期策略失败: {e}")

    try:
        await run_analysis_for_all_users()
    except Exception as e:
        logger.error(f"[定时任务] 学习分析失败: {e}", exc_info=True)

    logger.info("[定时任务] 学习行为分析完成")


async def _scheduler_loop():
    """调度器主循环"""
    ANALYSIS_INTERVAL_HOURS = 5  # 默认值

    while _running:
        try:
            from app.services.learning_analyzer import ANALYSIS_INTERVAL_HOURS as interval
            ANALYSIS_INTERVAL_HOURS = interval
        except Exception:
            pass  # 使用默认值

        now = datetime.now()
        logger.info(f"[调度器] 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 执行分析任务
        try:
            await _analysis_job()
        except Exception as e:
            logger.error(f"[调度器] 分析任务异常: {e}", exc_info=True)

        # 等待下一个周期
        wait_seconds = ANALYSIS_INTERVAL_HOURS * 3600
        logger.info(f"[调度器] 下次执行: {wait_seconds / 3600} 小时后")

        await asyncio.sleep(wait_seconds)


def start_scheduler():
    """启动调度器"""
    global _running, _task

    if _running:
        logger.warning("[调度器] 已经在运行")
        return

    _running = True
    _task = asyncio.create_task(_scheduler_loop())
    logger.info("[调度器] 已启动")


def stop_scheduler():
    """停止调度器"""
    global _running, _task

    if not _running:
        return

    _running = False
    if _task:
        _task.cancel()
        _task = None
    logger.info("[调度器] 已停止")
