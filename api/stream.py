from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.request import (
    QueryRequest
)

from rag.pipeline import (
    rag_pipeline
)

router = APIRouter()

@router.post("/stream")
async def stream_query(request: QueryRequest):
    async def event_stream():
        async for chunk in (
            rag_pipeline.astream(
                query=request.query,
                session_id=request.session_id
            )
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/plain"
    )