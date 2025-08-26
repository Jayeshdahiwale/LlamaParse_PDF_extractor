# parse.py
import asyncio
import tempfile
import os
from dataclasses import dataclass
from typing import List, Optional, Literal

import pdfplumber
from llama_cloud_services import LlamaParse
import config


@dataclass
class PageData:
    page_number: int
    content: str
    tables: Optional[List[List[List[str]]]] = None

class PDFExtractor:
    """
    Extracts full content from a PDF using either pdfplumber or LlamaParse.
    Reads system prompt from an optional file path.
    """
    

    def __init__(self, pdf_path: str, llama_api_key: Optional[str] = None, prompt_path: Optional[str] = None):
        self.pdf_path = pdf_path
        self.llama_api_key = llama_api_key
        self.user_prompt = self._load_prompt(prompt_path) if prompt_path else ""

    def _load_prompt(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            raise ValueError(f"Failed to read prompt from '{path}': {e}")

    def extract(
        self,
        parser_type: Literal["pdfplumber", "llama_parser"] = "pdfplumber"
    ) -> List[PageData]:
        if parser_type == "pdfplumber":
            return self._extract_pdfplumber()
        elif parser_type == "llama_parser":
            if not self.llama_api_key:
                raise ValueError("An API key is required for llama_parser.")
            return asyncio.run(self._extract_llama_parser())
        else:
            raise ValueError(f"Unsupported parser_type: {parser_type}")

    def _extract_pdfplumber(self) -> List[PageData]:
        pages: List[PageData] = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(layout=True) or ""
                tables = page.extract_tables() or []
                pages.append(PageData(page_number=i, content=text, tables=tables))
        return pages

    async def _extract_llama_parser(self) -> List[PageData]:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(open(self.pdf_path, "rb").read())
            tmp_path = tmp.name

        try:
            parser = LlamaParse(
                api_key=self.llama_api_key,
                system_prompt=self.user_prompt,
                parse_mode="parse_page_with_lvm",
                vendor_multimodal_model_name="gemini-2.5-pro",
                result_type="text",
                split_by_page=True,
                layout_extraction=True,
                page_separator="\n\n--- PAGE BREAK ---\n\n"
            )
            docs = await parser.aload_data(tmp_path)

            return [
                PageData(
                    page_number=int(doc.metadata.get("page_number", i + 1)),
                    content=doc.text.strip(),
                    tables=None
                )
                for i, doc in enumerate(docs)
            ]

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
