from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from core.config import settings
from observability.metrics import metrics_collector

DocumentRow = dict[str, Any]


@dataclass(frozen=True)
class EmbeddingConfig:
    input_path: str
    output_path: str
    model_name: str
    batch_size: int = 32


class DocumentEmbedder:
    """
    Local embedding pipeline for processed document chunks.

    Input rows must contain the columns produced by DocumentIngestion:
    chunk_id, document_id, source_path, file_name, page_number, chunk_index, text.
    """

    def __init__(
        self,
        input_path: str | None = None,
        output_path: str | None = None,
        model_name: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.config = EmbeddingConfig(
            input_path=input_path or settings.PROCESSED_DOCS_PATH,
            output_path=output_path or settings.EMBEDDED_DOCS_PATH,
            model_name=model_name or settings.HF_EMBEDDING_MODEL,
            batch_size=batch_size or settings.EMBEDDING_BATCH_SIZE,
        )
        self._model = None

    def load_document(self, input_path: str | None = None) -> list[DocumentRow]:
        """
        Load processed chunk Parquet created by DocumentIngestion.save_document().
        """
        return self._read_parquet(input_path or self.config.input_path)

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate one embedding locally. Useful for tests and query embedding.
        """
        embedding = self._get_model().encode([text], normalize_embeddings=True)[0]
        return [float(value) for value in embedding]

    def embed_query(self, text: str) -> np.ndarray:
        """
        Generate a query embedding as a numpy array for callers that use .tolist().
        """
        return np.asarray(self.generate_embedding(text), dtype=float)

    def process_document(self, chunks: list[DocumentRow] | None = None) -> list[DocumentRow]:
        """
        Add embedding vectors to every chunk row.
        """
        start_time = time.perf_counter()
        rows = chunks if chunks is not None else self.load_document()
        embedded_rows: list[DocumentRow] = []
        model = self._get_model()

        for batch in self._batch_rows(rows, self.config.batch_size):
            texts = [row["text"] for row in batch]
            embeddings = model.encode(texts, normalize_embeddings=True)

            for row, embedding in zip(batch, embeddings, strict=True):
                embedded_rows.append(
                    {
                        **row,
                        "embedding_model": self.config.model_name,
                        "embedding": [float(value) for value in embedding],
                    }
                )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector.record("embedding_chunks_processed", len(embedded_rows))
        metrics_collector.record("embedding_processing_time_ms", elapsed_ms)
        metrics_collector.record("embedding_model_used", self.config.model_name)
        return embedded_rows

    def save_document(
        self,
        embedded_rows: list[DocumentRow] | None = None,
        output_path: str | None = None,
        mode: str = "overwrite",
    ) -> str:
        """
        Save embedded chunks as local Parquet and return the output path.
        """
        destination = output_path or self.config.output_path
        rows = embedded_rows if embedded_rows is not None else self.process_document()
        self._write_parquet(rows, destination, mode)
        return destination

    def _get_model(self):
        if self._model is None:
            self._model = self._load_embedding_model(self.config.model_name)
        return self._model

    @staticmethod
    def _load_embedding_model(model_name: str):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)

    @staticmethod
    def _batch_rows(rows: Iterable[DocumentRow], batch_size: int) -> Iterable[list[DocumentRow]]:
        batch: list[DocumentRow] = []
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    @staticmethod
    def _read_parquet(input_path: str) -> list[DocumentRow]:
        import pandas as pd

        path = Path(input_path)
        if path.is_dir():
            files = sorted(path.glob("*.parquet"))
            if not files:
                return []
            dataframe = pd.concat((pd.read_parquet(file_path) for file_path in files), ignore_index=True)
        else:
            dataframe = pd.read_parquet(path)

        return dataframe.to_dict(orient="records")

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


document_embedder = DocumentEmbedder()
