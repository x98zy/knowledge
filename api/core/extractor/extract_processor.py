from common.entites import Document, ExtractSetting
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
        pass
