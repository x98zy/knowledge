import os
import tempfile

from sqlalchemy import select

from common.entites import Document, ExtractSetting
from config.settings import settings
from extensions.ext_db import db
from extensions.ext_storage import storage
from models.document import UploadFile

SUPPORT_URL_CONTENT_TYPES = ["application/pdf", "text/plain", "application/json"]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124"
    " Safari/537.36"
)


class ExtractProcessor:
    @classmethod
    def load_from_upload_file(
        cls, upload_file: UploadFile, return_text: bool = False, is_automatic: bool = False
    ) -> list[Document] | str:
        pass

    @classmethod
    def load_from_url(cls, url: str, return_text: bool = False) -> list[Document] | str:
        pass

    @classmethod
    async def extract(
        cls, extract_setting: ExtractSetting, is_automatic: bool = False, file_path: str | None = None
    ) -> list[Document]:
        query = select(UploadFile).where(UploadFile.file_key == extract_setting.upload_file.file_key)
        upload_file = await db.session.execute(query)
        upload_file = upload_file.scalars().first()
        if not upload_file:
            raise RuntimeError(f"Upload file not found: {extract_setting.upload_file.file_key}")
        suffix = (
            os.path.splitext(upload_file.file_name)[-1]
            if upload_file.file_name and "." in upload_file.file_name
            else ""
        )
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            await storage.download_file(upload_file.file_key, tmp.name)
            if suffix == ".txt":
                from core.extractor.text_extractor import TextExtractor

                return await TextExtractor(tmp.name, encoding="utf-8").extract()
            elif suffix in [".md", ".markdown"]:
                from core.extractor.markdown_extractor import MarkdownExtractor

                return await MarkdownExtractor(tmp.name).extract()
            elif suffix in [".xls", ".xlsx"]:
                from core.extractor.excel_extractor import ExcelExtractor

                return await ExcelExtractor(tmp.name).extract()
            elif suffix == ".csv":
                from core.extractor.csv_extractor import CSVExtractor

                return await CSVExtractor(tmp.name, encoding="utf-8").extract()
            elif suffix in [".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".html", ".wps"]:
                from core.extractor.textin_extractor import TextinExtractor

                return await TextinExtractor(tmp.name, settings.TEXTIN_APP_ID, settings.TEXTIN_SECRET_CODE).extract()
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
