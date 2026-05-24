from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

from core.config import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from observability.metrics import metrics_collector

logger = logging.getLogger(__name__)

DocumentRow = dict[str, Any]


@dataclass(frozen=True)
class IngestionConfig:
    source_path: str
    chunk_size: int = 1200
    chunk_overlap: int = 300


class DocumentIngestion:
    """
    Local PDF ingestion pipeline.

    Extracts PDF text page by page, chunks it, and returns embedding-ready
    dictionaries without requiring Spark.
    """

    def __init__(
        self,
        source_path: str = settings.DOCUMENT_SOURCE_PATH,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> None:
        self.config = IngestionConfig(
            source_path=source_path or settings.DOCUMENT_SOURCE_PATH,
            chunk_size=chunk_size or settings.CHUNK_SIZE,
            chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
        )

    def load_document(self, source_path: str | None = None) -> list[DocumentRow]:
        """
        Load PDF files from the configured path and return one row per PDF page.
        """
        pdf_paths = self._resolve_pdf_paths(source_path or self.config.source_path)
        pages: list[DocumentRow] = []

        for pdf_path in pdf_paths:
            try:
                pages.extend(self._extract_pdf_pages(pdf_path, pdf_path.read_bytes()))
            except Exception as exc:
                logger.error(f"Failed loading PDF {pdf_path}: {exc}")

        return pages

    def generate_chunk_id(
        self,
        source_path: str,
        page_number: int,
        chunk_index: int,
        text: str,
    ) -> str:
        return self._generate_chunk_id(source_path, page_number, chunk_index, text)

    def process_document(self, source_path: str | None = None) -> list[DocumentRow]:
        """
        Load PDFs and return embedding-ready chunks with stable metadata.
        """
        start_time = time.perf_counter()
        pages = self.load_document(source_path)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        chunks: list[DocumentRow] = []
        pages_count = len(pages)
        for page in pages:
            for chunk_index, chunk_text in enumerate(text_splitter.split_text(page["text"])):
                chunks.append(
                    {
                        "chunk_id": self._generate_chunk_id(
                            page["source_path"],
                            page["page_number"],
                            chunk_index,
                            chunk_text,
                        ),
                        "document_id": page["document_id"],
                        "source_path": page["source_path"],
                        "file_name": page["file_name"],
                        "page_number": page["page_number"],
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                    }
                )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector.record("ingestion_pages_processed", pages_count)
        metrics_collector.record("ingestion_chunks_created", len(chunks))
        metrics_collector.record("ingestion_processing_time_ms", elapsed_ms)
        logger.info(f"Processed {pages_count} pages into {len(chunks)} chunks in {elapsed_ms:.2f}ms")
        return chunks

    def save_document(
        self,
        chunks: list[DocumentRow] | None = None,
        output_path: str | None = None,
        mode: str = "overwrite",
    ) -> str:
        """
        Save processed document chunks as local Parquet.
        """
        start_time = time.perf_counter()
        destination = output_path or settings.PROCESSED_DOCS_PATH
        rows = chunks if chunks is not None else self.process_document()
        self._write_parquet(rows, destination, mode)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector.record("ingestion_save_time_ms", elapsed_ms)
        metrics_collector.record("ingestion_chunks_saved", len(rows))
        logger.info(f"Saved {len(rows)} chunks in {elapsed_ms:.2f}ms to {destination}")
        return destination

    @staticmethod
    def _resolve_pdf_paths(source_path: str) -> list[Path]:
        path = DocumentIngestion._to_local_path(source_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF source path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() != ".pdf":
                raise ValueError(f"Only PDF files are supported: {path}")
            return [path]

        return sorted(candidate for candidate in path.glob("*.pdf") if candidate.is_file())

    @staticmethod
    def _to_local_path(source_path: str) -> Path:
        if "://" not in source_path:
            return Path(source_path).expanduser()

        parsed = urlparse(source_path)
        if parsed.scheme != "file":
            raise ValueError(f"Only local file paths are supported: {source_path}")

        path_text = unquote(parsed.path)
        if os.name == "nt" and path_text.startswith("/") and len(path_text) > 2 and path_text[2] == ":":
            path_text = path_text[1:]

        return Path(path_text).expanduser()

    @staticmethod
    def _extract_pdf_pages(source_path: Path, content: bytes) -> Iterable[DocumentRow]:
        try:
            reader = PdfReader(BytesIO(content))
            normalized_source_path = str(source_path.resolve())
            document_id = hashlib.sha256(normalized_source_path.encode("utf-8")).hexdigest()

            for page_index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                cleaned_text = " ".join(text.split())
                if cleaned_text:
                    yield {
                        "document_id": document_id,
                        "source_path": normalized_source_path,
                        "file_name": source_path.name,
                        "page_number": page_index,
                        "text": cleaned_text,
                    }
        except Exception as exc:
            logger.error(f"Failed parsing PDF {source_path}: {exc}")

    @staticmethod
    def _generate_chunk_id(
        source_path: str,
        page_number: int,
        chunk_index: int,
        text: str,
    ) -> str:
        raw_id = f"{source_path}|{page_number}|{chunk_index}|{text}"
        return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()

    @staticmethod
    def _write_parquet(rows: list[DocumentRow], destination: str, mode: str) -> None:
        import pandas as pd

        dest_path = Path(destination)
        if dest_path.exists() and mode == "overwrite":
            if dest_path.is_dir():
                for file_path in dest_path.glob("*.parquet"):
                    file_path.unlink()
            else:
                dest_path.unlink()

        if dest_path.suffix == ".parquet":
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_parquet(dest_path, index=False)
            return

        dest_path.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_parquet(dest_path / "part-00000-local.parquet", index=False)


document_ingestion = DocumentIngestion()
