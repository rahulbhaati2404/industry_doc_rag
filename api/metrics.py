from fastapi import APIRouter

from observability.metrics import (
    metrics_collector
)

router = APIRouter()

@router.get("/metrics")
async def metrics():

    return metrics_collector.summary()