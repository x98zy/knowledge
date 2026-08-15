from datetime import timedelta
from logging import getLogger

import aiofiles
import alibabacloud_oss_v2 as oss
import alibabacloud_oss_v2.aio as oss_aio

from config.settings import settings

logger = getLogger(__name__)


class AliYunOSS:
    def __init__(self, access_key: str, access_key_secret: str, bucket: str, region: str):
        self.access_key = access_key
        self.access_key_secret = access_key_secret
        self.bucket = bucket
        self.region = region

        credentials_provider = oss.credentials.StaticCredentialsProvider(self.access_key, self.access_key_secret)
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider
        cfg.region = self.region

        self.client = oss_aio.AsyncClient(cfg)
        self.sync_client = oss.Client(cfg)

    async def put_object(self, file_name: str, file_key: str):
        async with aiofiles.open(file_name, "rb") as f:
            data = await f.read()
            result = await self.client.put_object(
                oss.PutObjectRequest(
                    bucket=self.bucket,
                    key=file_key,
                    body=data,
                )
            )
            logger.info(f"上传文件 {file_name} 到 OSS status_code={result.status_code}")

    async def download_file(self, file_key: str, file_path: str):
        """从 OSS 下载文件, file_key"""
        result = await self.client.get_object(
            oss.GetObjectRequest(
                bucket=self.bucket,
                key=file_key,
            )
        )
        logger.info(f"下载文件 {file_key} status_code={result.status_code}")
        data = await result.body.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)
        logger.info(f"文件下载完成，保存至路径：{file_path}")

    def get_signed_url(self, file_key: str, expire: int = 3600):
        """获取 OSS 签名 URL, file_key"""
        result = self.sync_client.presign(
            oss.GetObjectRequest(
                bucket=self.bucket,
                key=file_key,
            ),
            expires=timedelta(seconds=expire),
        )
        logger.info(f"获取 OSS 签名 URL {file_key} url={result.url}")
        return result.url


storage = AliYunOSS(
    access_key=settings.ALIYUN_OSS_ACCESS_KEY,
    access_key_secret=settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
    bucket=settings.ALIYUN_OSS_BUCKET,
    region=settings.ALIYUN_OSS_REGION,
)
