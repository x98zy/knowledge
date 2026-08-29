"""Abstract interface for document loader implementations."""

import aiofiles

from common.entites import Document
from core.extractor.extractor_base import BaseExtractor
from core.extractor.helpers import detect_file_encodings


class TextExtractor(BaseExtractor):
    """Load text files.


    Args:
        file_path: Path to the file to load.
    """

    def __init__(self, file_path: str, encoding: str | None = None, autodetect_encoding: bool = False):
        """Initialize with file path."""
        self._file_path = file_path
        self._encoding = encoding
        self._autodetect_encoding = autodetect_encoding

    async def extract(self) -> list[Document]:
        """Load from file path."""
        text = ""
        try:
            async with aiofiles.open(self._file_path, encoding=self._encoding) as f:
                text = await f.read()
        except UnicodeDecodeError as e:
            if self._autodetect_encoding:
                detected_encodings = await detect_file_encodings(self._file_path)
                for encoding in detected_encodings:
                    try:
                        async with aiofiles.open(self._file_path, encoding=encoding.encoding) as f:
                            text = await f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise RuntimeError(
                        f"Decode failed: {self._file_path}, all detected encodings failed. Original error: {e}"
                    )
            else:
                raise RuntimeError(f"Decode failed: {self._file_path}, specified encoding failed. Original error: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading {self._file_path}") from e

        metadata = {"source": self._file_path}
        return [Document(page_content=text, metadata=metadata)]
