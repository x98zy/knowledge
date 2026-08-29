"""Abstract interface for document loader implementations."""

import asyncio
import os
from typing import cast

import pandas as pd
from openpyxl import load_workbook

from common.entites import Document
from core.extractor.extractor_base import BaseExtractor


class ExcelExtractor(BaseExtractor):
    """Load Excel files.


    Args:
        file_path: Path to the file to load.
    """

    def __init__(self, file_path: str, encoding: str | None = None, autodetect_encoding: bool = False):
        """Initialize with file path."""
        self._file_path = file_path
        self._encoding = encoding
        self._autodetect_encoding = autodetect_encoding

    async def extract(self) -> list[Document]:
        """Load from Excel file in xls or xlsx format using Pandas and openpyxl."""
        # Excel 解析(openpyxl/pandas)是 CPU 密集的同步操作，放线程池执行避免阻塞事件循环
        file_extension = os.path.splitext(self._file_path)[-1].lower()

        # 这里将耗时的文件解析放到线程池里面去执行，避免阻塞时间循环
        if file_extension == ".xlsx":
            return await asyncio.to_thread(self._load_xlsx)
        elif file_extension == ".xls":
            return await asyncio.to_thread(self._load_xls)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")

    def _load_xlsx(self) -> list[Document]:
        documents = []
        wb = load_workbook(self._file_path, data_only=True)
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            data = sheet.values
            cols = next(data, None)
            if cols is None:
                continue
            df = pd.DataFrame(data, columns=cols)

            df.dropna(how="all", inplace=True)

            for index, row in df.iterrows():
                page_content = []
                for col_index, (k, v) in enumerate(row.items()):
                    if pd.notna(v):
                        cell = sheet.cell(
                            row=cast("int", index) + 2, column=col_index + 1
                        )  # +2 to account for header and 1-based index
                        if cell.hyperlink:
                            value = f"[{v}]({cell.hyperlink.target})"
                            page_content.append(f'"{k}":"{value}"')
                        else:
                            page_content.append(f'"{k}":"{v}"')
                documents.append(Document(page_content=";".join(page_content), metadata={"source": self._file_path}))
        return documents

    def _load_xls(self) -> list[Document]:
        documents = []
        excel_file = pd.ExcelFile(self._file_path, engine="xlrd")
        for excel_sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name=excel_sheet_name)
            df.dropna(how="all", inplace=True)

            for _, row in df.iterrows():
                page_content = []
                for k, v in row.items():
                    if pd.notna(v):
                        page_content.append(f'"{k}":"{v}"')
                documents.append(Document(page_content=";".join(page_content), metadata={"source": self._file_path}))
        return documents
