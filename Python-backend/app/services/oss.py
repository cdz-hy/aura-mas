import os
from qiniu import Auth, put_file, etag
from app.core.config import settings

class QiniuOSSService:
    def __init__(self):
        self.q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
        self.bucket_name = settings.QINIU_BUCKET_NAME
        self.domain = settings.QINIU_DOMAIN

    def upload_file(self, local_file_path: str, remote_file_name: str) -> str:
        """
        上传文件到七牛云并返回公网访问 URL
        """
        token = self.q.upload_token(self.bucket_name, remote_file_name, 3600)
        ret, info = put_file(token, remote_file_name, local_file_path, version='v2')
        
        if info.status_code == 200:
            # 确保域名以 / 结尾
            base_url = self.domain if self.domain.endswith('/') else f"{self.domain}/"
            return f"{base_url}{remote_file_name}"
        else:
            raise Exception(f"七牛云上传失败: {info.text_body}")
