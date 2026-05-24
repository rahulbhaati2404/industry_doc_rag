from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Embedding, Metadata
from chromadb.errors import NotFoundError

from core.config import settings
from observability.metrics import metrics_collector

DocumentRow = dict[str, Any]


@dataclass(frozen=True)
class VectorStoreConfig:
    input_path: str
    persist_dir: str
    collection_name: str
    batch_size: int = 100


class DocumentVectorStore:
    """
    Stores embedded document chunks in ChromaDB.

    Input rows must contain the columns produced by DocumentEmbedder:
    chunk_id, document_id, source_path, file_name, page_number, chunk_index,
    text, embedding_model, embedding.
    """

    REQUIRED_COLUMNS = {
        "chunk_id",
        "document_id",
        "source_path",
        "file_name",
        "page_number",
        "chunk_index",
        "text",
        "embedding_model",
        "embedding",
    }

    def __init__(
        self,
        input_path: str | None = None,
        persist_dir: str | None = None,
        collection_name: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.config = VectorStoreConfig(
            input_path=input_path or settings.EMBEDDED_DOCS_PATH,
            persist_dir=persist_dir or settings.CHROMA_PERSIST_DIR,
            collection_name=collection_name or settings.CHROMA_COLLECTION_NAME,
            batch_size=batch_size or settings.VECTOR_STORE_BATCH_SIZE,
        )
        self._client = None
        self._collection: Collection | None = None

    @property
    def client(self):
        if self._client is None:
            self._client = self._create_client()
        return self._client

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            self._collection = self.get_collection()
        return self._collection

    def load_document(self, input_path: str | None = None) -> list[DocumentRow]:
        """
        Load embedded chunk Parquet created by DocumentEmbedder.save_document().
        """
        rows = self._read_parquet(input_path or self.config.input_path)
        self._validate_rows(rows)
        return rows

    def get_collection(self) -> Collection:
        """
        Create or return the configured Chroma collection.
        """
        return self.client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def store_document(self, embedded_rows: list[DocumentRow] | None = None) -> int:
        """
        Store embedded chunks in ChromaDB and return the number of rows upserted.
        """
        start_time = time.perf_counter()
        rows = embedded_rows if embedded_rows is not None else self.load_document()
        self._validate_rows(rows)

        total_rows = 0
        for batch in self._batch_rows(rows, self.config.batch_size):
            payload = self._build_chroma_payload(batch)
            self.collection.upsert(**payload)
            total_rows += len(batch)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector.record("vector_store_chunks_upserted", total_rows)
        metrics_collector.record("vector_store_upsert_time_ms", elapsed_ms)
        metrics_collector.record("vector_store_collection", self.config.collection_name)
        return total_rows

    def similarity_search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """
        Query ChromaDB using the same local embedding model used for ingestion.
        """
        from rag.embedder import document_embedder

        embedding = document_embedder.generate_embedding(query)
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

    def count_documents(self) -> int:
        """
        Return the number of chunks currently stored in the Chroma collection.
        """
        return self.collection.count()

    def reset_collection(self) -> Collection:
        """
        Delete and recreate the configured collection.
        """
        try:
            self.client.delete_collection(self.config.collection_name)
        except NotFoundError:
            pass

        self._collection = self.get_collection()
        return self._collection

    def _create_client(self):
        Path(self.config.persist_dir).mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=self.config.persist_dir)

    @classmethod
    def _validate_rows(cls, rows: list[DocumentRow]) -> None:
        if not rows:
            return

        missing_columns = cls.REQUIRED_COLUMNS.difference(rows[0].keys())
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Embedded rows are missing required columns: {missing}")

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
    def _build_chroma_payload(rows: list[DocumentRow]) -> dict[str, list[Any]]:
        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[Embedding] = []
        metadatas: list[Metadata] = []

        for row in rows:
            ids.append(row["chunk_id"])
            documents.append(row["text"])
            embeddings.append([float(value) for value in row["embedding"]])
            metadatas.append(
                {
                    "document_id": row["document_id"],
                    "source_path": row["source_path"],
                    "file_name": row["file_name"],
                    "page_number": int(row["page_number"]),
                    "chunk_index": int(row["chunk_index"]),
                    "embedding_model": row["embedding_model"],
                }
            )

        return {
            "ids": ids,
            "documents": documents,
            "embeddings": embeddings,
            "metadatas": metadatas,
        }

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


vector_store = DocumentVectorStore()
