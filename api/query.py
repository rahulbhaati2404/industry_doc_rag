from fastapi import APIRouter

from schemas.request import QueryRequest
from schemas.response import QueryResponse

from rag.pipeline import rag_pipeline

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse
)
async def query_rag(
    request: QueryRequest
):

    result = await rag_pipeline.arun(
        query=request.query,
        session_id=request.session_id
    )

    return result
