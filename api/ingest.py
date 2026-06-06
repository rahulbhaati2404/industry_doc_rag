from pathlib import Path
from typing import Any
import time
from fastapi import APIRouter, File, UploadFile
from core.config import settings
from core.logger import logger
from observability.metrics import metrics_collector
from rag.embedder import document_embedder
from rag.ingestion import document_ingestion
from rag.vector_store import vector_store

router = APIRouter()

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)) -> dict[str, Any]:
    """Complete PDF ingestion pipeline:

    1. Save PDF to data/raw/
    2. Extract and chunk text
    3. Generate embeddings
    4. Store in ChromaDB vector database
    """
    pipeline_start = time.perf_counter()
    try:
        save_path = f"data/raw/{file.filename}"
        Path("data/raw").mkdir(parents=True, exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(await file.read())

        logger.info(f"File saved: {save_path}")

        chunks = document_ingestion.process_document(save_path)
        chunks_count = len(chunks)
        document_ingestion.save_document(chunks)
        logger.info(f"Chunking complete: {chunks_count} chunks created")

        embedded_rows = document_embedder.process_document(chunks)
        document_embedder.save_document(embedded_rows)
        logger.info("Embedding complete: vectors generated")

        stored_count = vector_store.store_document(embedded_rows)
        logger.info(f"ChromaDB storage complete: {stored_count} chunks upserted")

        pipeline_elapsed_ms = (time.perf_counter() - pipeline_start) * 1000
        metrics_collector.record("api_ingest_total_time_ms", pipeline_elapsed_ms)
        metrics_collector.record("api_ingest_success", 1)

        return {
            "status": "success",
            "message": "PDF ingestion pipeline completed successfully",
            "filename": file.filename,
            "chunks_created": chunks_count,
            "chunks_embedded": stored_count,
            "pipeline_time_ms": pipeline_elapsed_ms,
            "storage_locations": {
                "raw_pdf": save_path,
                "processed_chunks": settings.PROCESSED_DOCS_PATH,
                "embedded_chunks": settings.EMBEDDED_DOCS_PATH,
                "vector_db": settings.CHROMA_PERSIST_DIR,
            },
        }

    except Exception as exc:
        pipeline_elapsed_ms = (time.perf_counter() - pipeline_start) * 1000
        metrics_collector.record("api_ingest_total_time_ms", pipeline_elapsed_ms)
        metrics_collector.record("api_ingest_failed", 1)
        logger.error(f"PDF ingestion failed: {exc}")
        return {"status": "error", "message": str(exc), "filename": file.filename}
