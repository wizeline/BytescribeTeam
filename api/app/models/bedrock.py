from pydantic import BaseModel, Field
from typing import Dict


class SummaryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=65536)
    request: str = ''


class SummaryResponse(BaseModel):
    result: Dict = {}
