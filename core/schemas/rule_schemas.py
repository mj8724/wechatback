from typing import Any, List, Optional
from pydantic import BaseModel


class RuleRequest(BaseModel):
    id: Optional[int] = None
    keyword: str = ""
    mode: str = "contains"
    action: str = "none"
    content: str = ""
    priority: int = 100
    enabled: bool = True
    recipe: Optional[str] = ""
    status_replies: Optional[Any] = None
    start_time: Optional[str] = ""
    end_time: Optional[str] = ""


class RuleBatchDeleteRequest(BaseModel):
    ids: List[int] = []


class RuleBatchToggleRequest(BaseModel):
    ids: List[int] = []
    enabled: bool


class RuleImportItem(BaseModel):
    keyword: str
    mode: str = "contains"
    action: str = "none"
    content: str = ""
    priority: int = 100
    enabled: bool = True
    recipe: str = ""
    status_replies: Optional[Any] = None
    start_time: Optional[str] = ""
    end_time: Optional[str] = ""


class RuleBatchImportRequest(BaseModel):
    mode: str = "skip"  # 'skip' | 'overwrite'
    rules: List[RuleImportItem] = []
