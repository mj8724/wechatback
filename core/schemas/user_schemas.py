from typing import List
from pydantic import BaseModel


class UserResetRequest(BaseModel):
    openid: str


class UserBatchResetRequest(BaseModel):
    openids: List[str] = []
