import hashlib
import json
import os
import tempfile
import uuid

import aiofiles
import httpx
from sqlalchemy import select, update

from common.entites import Document
from core.extractor.extractor_base import BaseExtractor
from extensions.ext_db import db
from extensions.ext_log import logger
from extensions.ext_storage import storage
from models.document import UploadFile


def create_temp_path(suffix: str) -> str:
    """生成一个立即可用的临时文件路径。

    Windows 下 NamedTemporaryFile 在 with 块内持有打开句柄时，再次用 open() 打开
    同名文件会抛 PermissionError [Errno 13]（Windows 不允许打开中的临时文件被二次打开）。
    这里用 mkstemp 创建后立即关闭句柄，只返回路径，由调用方在用完后 os.remove 删除。
    """
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        logger.warning(f"临时文件删除失败: {path}")


class TextinOCRClient:
    def __init__(self, app_id: str, secret_code: str) -> None:
        self.app_id = app_id
        self.secret_code = secret_code

    async def recognize(self, file_content: bytes, options: dict) -> str:
        # 构建请求参数
        params = {}
        for key, value in options.items():
            params[key] = str(value)

        # 设置请求头
        headers = {
            "x-ti-app-id": self.app_id,
            "x-ti-secret-code": self.secret_code,
            # 方式一：读取本地文件
            "Content-Type": "application/octet-stream",
        }

        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.textin.com/ai/service/v1/pdf_to_markdown",
                params=params,
                headers=headers,
                data=file_content,
            )
            response.raise_for_status()
            return response.text


class TextinExtractor(BaseExtractor):
    def __init__(self, file_path: str, app_id: str, secret_code: str) -> None:
        self.file_path = file_path
        self.app_id = app_id
        self.secret_code = secret_code

    async def extract(self) -> list[Document]:
        async with aiofiles.open(self.file_path, "rb") as f:
            data = await f.read()
            file_hash = hashlib.sha256(data).hexdigest()
            query = select(UploadFile).where(UploadFile.file_hash == file_hash, UploadFile.deleted == 0)
            result = await db.session.execute(query)
            upload_file = result.scalars().first()
            if upload_file and upload_file.parse_file_key:
                logger.info(f"File already processed, using cached result: {upload_file.parse_file_key}")
                tmp_path = create_temp_path(".md")
                try:
                    await storage.download_file(upload_file.parse_file_key, tmp_path)
                    async with aiofiles.open(tmp_path, encoding="utf-8") as f:
                        markdown_content = await f.read()
                        return [Document(page_content=markdown_content, metadata={})]
                finally:
                    safe_remove(tmp_path)
            else:
                logger.info(f"Textin Processing new file: {self.file_path}")
                textin_client = TextinOCRClient(self.app_id, self.secret_code)
                params = dict(
                    markdown_details=1,
                    parse_mode="auto",
                )
                resp_text = await textin_client.recognize(data, params)
                json_response = json.loads(resp_text)
                if "result" in json_response and "markdown" in json_response["result"]:
                    markdown_content = json_response["result"]["markdown"]
                    tmp_path = create_temp_path(".md")
                    try:
                        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
                            await f.write(markdown_content)
                        file_key = f"{uuid.uuid4()}.md"
                        await storage.put_object(file_name=tmp_path, file_key=file_key)
                        query = (
                            update(UploadFile)
                            .where(UploadFile.file_hash == file_hash, UploadFile.deleted == 0)
                            .values(parse_file_key=file_key)
                        )
                        await db.session.execute(query)
                    finally:
                        safe_remove(tmp_path)
                    return [Document(page_content=markdown_content, metadata={})]
