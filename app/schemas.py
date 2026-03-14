from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Union
from datetime import datetime

class AnalyzeRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

class AnalyzeResponse(BaseModel):
    query: str
    status: str
    response: Dict[str, Any] = Field(default_factory=dict)
    pdf_url: Optional[str] = None
    report_id: Optional[Union[int, str]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())