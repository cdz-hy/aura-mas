"""
MinerU API 客户端 - 文档解析服务（全异步）
"""
import os
import zipfile
import logging
import httpx
import asyncio
from pathlib import Path
from typing import Tuple
from app.core.config import settings
from app.services.qiniu_client import qiniu_client

logger = logging.getLogger("services.mineru")


class MinerUClient:
    """MinerU 文档解析 API 客户端（异步）"""

    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

    def __init__(self):
        self.api_key = settings.MINERU_API_KEY
        self.base_url = settings.MINERU_API_BASE.rstrip("/")

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_task(self, file_path: str) -> str:
        """
        创建解析任务：先上传文件到七牛云获取 URL，再提交给 MinerU

        Args:
            file_path: 本地文件路径

        Returns:
            task_id: 任务ID
        """
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise Exception(f"文件大小超过限制: {file_size / 1024 / 1024:.1f}MB，最大支持 200MB")

        # 1. 上传文件到七牛云获取公开 URL（七牛客户端是同步的，放线程池）
        logger.info(f"  [MinerU] 上传文件到七牛云...")
        loop = asyncio.get_running_loop()
        file_url = await loop.run_in_executor(None, qiniu_client.upload_file, file_path, "kb-uploads")
        logger.info(f"  [MinerU] 文件 URL: {file_url}")

        # 2. 提交解析任务给 MinerU
        url = f"{self.base_url}/extract/task"
        logger.info(f"  [MinerU] 提交解析任务: {url}")

        payload = {
            "url": file_url,
            "is_ocr": True,
            "enable_formula": True,
            "enable_table": True,
            "language": "ch",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=self._get_headers(), json=payload)

        if resp.status_code != 200:
            raise Exception(f"MinerU 创建任务失败: {resp.status_code} - {resp.text[:300]}")

        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"MinerU 返回错误: {result.get('msg', '未知错误')}")

        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            raise Exception(f"MinerU 未返回 task_id: {result}")

        logger.info(f"  [MinerU] 任务已创建: task_id={task_id}")
        return task_id

    async def poll_task(self, task_id: str, timeout: int = 600, interval: int = 5) -> dict:
        """
        轮询任务状态直到完成（异步，不阻塞事件循环）

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            interval: 轮询间隔（秒）

        Returns:
            任务结果，包含 full_zip_url
        """
        url = f"{self.base_url}/extract/task/{task_id}"
        start_time = asyncio.get_event_loop().time()

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise Exception(f"MinerU 任务超时 ({timeout}s): task_id={task_id}")

                resp = await client.get(url, headers=self._get_headers())

                if resp.status_code != 200:
                    logger.warning(f"  [MinerU] 轮询异常: {resp.status_code}")
                    await asyncio.sleep(interval)
                    continue

                result = resp.json()
                if result.get("code") != 0:
                    logger.warning(f"  [MinerU] 轮询返回错误: {result.get('msg')}")
                    await asyncio.sleep(interval)
                    continue

                data = result.get("data", {})
                state = data.get("state", "")

                if state == "done":
                    # 验证返回的数据完整性
                    zip_url = data.get("full_zip_url", "")
                    if not zip_url:
                        raise Exception(f"MinerU 任务完成但未返回下载链接: task_id={task_id}")
                    
                    # 打印完整的返回数据用于调试
                    logger.info(f"  [MinerU] 任务完成: task_id={task_id}")
                    logger.info(f"  [MinerU] 返回数据: {data}")
                    
                    return data
                elif state == "failed":
                    raise Exception(f"MinerU 任务失败: {data.get('err_msg', '未知错误')}")
                else:
                    logger.info(f"  [MinerU] 任务进行中: state={state}, elapsed={elapsed:.0f}s")
                    await asyncio.sleep(interval)

    async def download_and_extract(self, zip_url: str, dest_dir: str) -> Tuple[str, str]:
        """
        下载并解压 MinerU 输出的 zip 文件（异步）

        Args:
            zip_url: zip 文件下载链接
            dest_dir: 解压目标目录

        Returns:
            (md_file_path, images_dir_path)
        """
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        zip_path = dest_path / "output.zip"
        logger.info(f"  [MinerU] 下载结果: {zip_url[:80]}...")

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(zip_url)
            if resp.status_code != 200:
                raise Exception(f"下载 MinerU 结果失败: {resp.status_code}")

            with open(zip_path, "wb") as f:
                f.write(resp.content)

        logger.info(f"  [MinerU] 解压到: {dest_dir}")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(dest_path)

        zip_path.unlink(missing_ok=True)

        md_files = list(dest_path.rglob("*.md"))
        if not md_files:
            raise Exception(f"MinerU 输出中未找到 .md 文件: {dest_dir}")

        md_path = str(md_files[0])
        images_dir = str(dest_path / "images")
        if not Path(images_dir).exists():
            images_dir = ""

        logger.info(f"  [MinerU] MD文件: {md_path}")
        logger.info(f"  [MinerU] 图片目录: {images_dir or '无'}")

        return md_path, images_dir


# 全局单例
mineru_client = MinerUClient()
