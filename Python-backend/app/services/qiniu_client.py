"""
七牛云对象存储客户端
"""
import uuid
import logging
from pathlib import Path
from qiniu import Auth, put_data
from app.core.config import settings

logger = logging.getLogger("services.qiniu")


class QiniuClient:
    """七牛云 OSS 客户端"""

    def __init__(self):
        self.access_key = settings.QINIU_ACCESS_KEY
        self.secret_key = settings.QINIU_SECRET_KEY
        self.bucket_name = settings.QINIU_BUCKET_NAME
        self.domain = settings.QINIU_DOMAIN.rstrip("/")
        self.auth = Auth(self.access_key, self.secret_key)

    def upload_file(self, file_path: str, directory: str = "knowledge-base") -> str:
        """
        上传本地文件到七牛云

        Args:
            file_path: 本地文件路径
            directory: 存储目录

        Returns:
            文件的公开访问 URL
        """
        ext = Path(file_path).suffix
        key = f"{directory}/{uuid.uuid4()}{ext}"

        token = self.auth.upload_token(self.bucket_name, key, 3600)

        with open(file_path, "rb") as f:
            data = f.read()

        ret, info = put_data(token, key, data)
        if info.status_code == 200:
            url = f"{self.domain}/{key}"
            logger.info(f"  [Qiniu] 上传成功: {url}")
            return url
        else:
            raise Exception(f"七牛云上传失败: {info.status_code} - {info.error}")

    def upload_bytes(self, data: bytes, filename: str, directory: str = "knowledge-base") -> str:
        """
        上传字节数据到七牛云

        Args:
            data: 文件字节数据
            filename: 文件名（用于提取扩展名）
            directory: 存储目录

        Returns:
            文件的公开访问 URL
        """
        ext = Path(filename).suffix
        key = f"{directory}/{uuid.uuid4()}{ext}"

        token = self.auth.upload_token(self.bucket_name, key, 3600)

        ret, info = put_data(token, key, data)
        if info.status_code == 200:
            url = f"{self.domain}/{key}"
            logger.info(f"  [Qiniu] 上传成功: {url}")
            return url
        else:
            raise Exception(f"七牛云上传失败: {info.status_code} - {info.error}")

    def delete_by_url(self, url: str):
        """根据完整 URL 删除七牛云文件"""
        base = self.domain + "/"
        if not url.startswith(base):
            return
        key = url[len(base):]
        try:
            from qiniu import BucketManager
            bucket_manager = BucketManager(self.auth)
            bucket_manager.delete(self.bucket_name, key)
            logger.info(f"  [Qiniu] 删除成功: {key}")
        except Exception as e:
            logger.warning(f"  [Qiniu] 删除失败: {key}, {e}")


# 全局单例
qiniu_client = QiniuClient()
