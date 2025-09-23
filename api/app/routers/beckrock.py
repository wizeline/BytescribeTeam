import logging
from fastapi import APIRouter, HTTPException
from typing import List
from app.models.bedrock import (
    SummaryResponse,
    # SummaryRequest
)
from app.utils.bedrock import bedrock_runtime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bedrock", tags=["bedrock"])


@router.post(
    "/summary",
    response_model=SummaryResponse,
    status_code=200
)
def summaries():
    try:
        result = bedrock_runtime.summarize_page()
        return SummaryResponse(**result)
    except Exception as ex:
        logger.error(f"---> summaries: Meet an exception {ex}")
        raise HTTPException(500, str(ex))


@router.get(
    "/{task_id}",
    response_model=List[SummaryResponse],
    status_code=200
)
def get_status(task_id: int):
    pass
