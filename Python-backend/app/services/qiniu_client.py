"""
七牛云对象存储客户端
"""
import logging
import uuid
from pathlib import Path
from urllib.parse import urlparse

from qiniu import Auth, BucketManager, put_data
import qiniu.config as qiniu_config

from app.core.config import settings

logger = logging.getLogger("services.qiniu")

# 大文件上传需要更长超时（默认30s不够）
qiniu_config.set_default(connection_timeout=120)


class QiniuClient:
    """七牛云 OSS 客户端"""

    def __init__(self):
        self.access_key = settings.QINIU_ACCESS_KEY
        self.secret_key = settings.QINIU_SECRET_KEY
        self.bucket_name = settings.QINIU_BUCKET_NAME
        self.auth = Auth(self.access_key, self.secret_key)
        self._configured_domain = (settings.QINIU_DOMAIN or "").rstrip("/")
        self._resolved_domain: str | None = None
        self.domain = self._configured_domain

    def _list_bound_domains(self) -> list[str]:
        try:
            bm = BucketManager(self.auth)
            ret, info = bm.list_domains(self.bucket_name)
            if info.status_code != 200 or not ret:
                logger.warning("  [Qiniu] list_domains failed: %s", getattr(info, "error", info.status_code))
                return []
            domains: list[str] = []
            for item in ret:
                if isinstance(item, str) and item.strip():
                    domains.append(item.strip().lower())
                elif isinstance(item, dict) and item.get("domain"):
                    domains.append(str(item["domain"]).strip().lower())
            return domains
        except Exception as exc:
            logger.warning("  [Qiniu] list_domains error: %s", exc)
            return []

    def resolve_public_domain(self) -> str:
        """Return a working public base URL for this bucket.

        Prefer configured QINIU_DOMAIN when it is bound to the bucket; otherwise
        fall back to the first domain returned by Qiniu list_domains.
        """
        if self._resolved_domain:
            return self._resolved_domain

        configured = self._configured_domain
        configured_host = urlparse(configured).netloc.lower() if configured else ""
        bound = self._list_bound_domains()

        chosen = configured
        if bound:
            if configured_host and configured_host in bound:
                chosen = configured if "://" in configured else f"http://{configured_host}"
            else:
                host = bound[0]
                chosen = f"http://{host}"
                if configured_host and configured_host not in bound:
                    logger.warning(
                        "  [Qiniu] QINIU_DOMAIN host %s is not bound to bucket %s; using %s",
                        configured_host,
                        self.bucket_name,
                        chosen,
                    )
        elif not chosen:
            raise Exception("QINIU_DOMAIN is empty and no bucket domains are bound")

        self._resolved_domain = chosen.rstrip("/")
        self.domain = self._resolved_domain
        return self._resolved_domain

    def allowed_audio_hosts(self) -> set[str]:
        hosts: set[str] = set(self._list_bound_domains())
        for base in (self._configured_domain, self._resolved_domain or "", self.domain or ""):
            host = urlparse(base if "://" in base else f"http://{base}").netloc.lower()
            if host:
                hosts.add(host)
        return hosts

    def rewrite_to_public_url(self, url: str) -> str:
        """Rewrite an object URL onto the bucket's active public domain (keeps path/query)."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc or not parsed.path:
            return url
        public = self.resolve_public_domain().rstrip("/")
        return f"{public}{parsed.path}" + (f"?{parsed.query}" if parsed.query else "")

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
            url = f"{self.resolve_public_domain()}/{key}"
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
            url = f"{self.resolve_public_domain()}/{key}"
            logger.info(f"  [Qiniu] 上传成功: {url}")
            return url
        else:
            raise Exception(f"七牛云上传失败: {info.status_code} - {info.error}")

    def delete_by_url(self, url: str):
        """根据完整 URL 删除七牛云文件"""
        parsed = urlparse(url)
        key = parsed.path.lstrip("/")
        if not key:
            return
        try:
            bucket_manager = BucketManager(self.auth)
            bucket_manager.delete(self.bucket_name, key)
            logger.info(f"  [Qiniu] 删除成功: {key}")
        except Exception as e:
            logger.warning(f"  [Qiniu] 删除失败: {key}, {e}")


# 全局单例
qiniu_client = QiniuClient()
