from typing import Dict, List, Optional
from pydantic import BaseModel


class ImportRequest(BaseModel):
    pool_id: Optional[int] = 1
    codes: List[str] = []
    multi_pool_codes: Optional[Dict[str, List[str]]] = None


class PoolCreateRequest(BaseModel):
    name: str
    key: str
    description: str = ""


class PoolUpdateRequest(BaseModel):
    name: str
    description: str = ""


class CodeRequest(BaseModel):
    code: str
