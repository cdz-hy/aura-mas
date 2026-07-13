"""
定时任务调度器 - 基于用户活跃时间触发分析
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("services.scheduler")

# 任务运行状态
_running = False
_task = None

# 检查间隔（秒）
CHECK_INTERVAL = 1800  # 每30分钟检查一次


async def _analysis_job():
    """学习分析任务"""
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


async def _check_and_analyze():
    """检查用户活跃时间并触发分析"""
    from app.services.db.java_client import java_client
    from app.services.learning_analyzer import run_analysis_for_user

    try:
        # 获取需要分析的用户
        active_user_ids = await asyncio.to_thread(
            java_client._request, "GET", "/api/tracker/internal/active-users",
            params={"hours": 24}  # 获取最近24小时活跃的用户
        )

        if not active_user_ids or not isinstance(active_user_ids, list):
            return

        logger.info(f"[调度器] 检查 {len(active_user_ids)} 个用户的活跃时间")

        for user_id in active_user_ids:
            try:
                # 检查用户是否需要分析
                need_analysis = await asyncio.to_thread(
                    java_client._request, "GET", "/api/tracker/internal/need-analysis",
                    params={"userId": user_id}
                )

                if need_analysis:
                    logger.info(f"[调度器] 用户 {user_id} 活跃时间达到5小时，开始分析")
                    await run_analysis_for_user(user_id)
                    logger.info(f"[调度器] 用户 {user_id} 分析完成")
                else:
                    logger.debug(f"[调度器] 用户 {user_id} 活跃时间不足，跳过")

            except Exception as e:
                logger.error(f"[调度器] 用户 {user_id} 检查失败: {e}")

    except Exception as e:
        logger.error(f"[调度器] 检查用户活跃时间失败: {e}", exc_info=True)


async def _scheduler_loop():
    """调度器主循环 - 每分钟检查一次"""
    logger.info("[调度器] 启动，每分钟检查用户活跃时间")

    while _running:
        now = datetime.now()
        logger.debug(f"[调度器] 检查时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 检查用户活跃时间并触发分析
        try:
            await _check_and_analyze()
        except Exception as e:
            logger.error(f"[调度器] 检查任务异常: {e}", exc_info=True)

        # 等待下一次检查
        await asyncio.sleep(CHECK_INTERVAL)


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
