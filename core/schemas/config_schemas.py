from typing import Optional
from pydantic import BaseModel


class SetupRequest(BaseModel):
    admin_password: str
    wechat_token: str = ""
    website_url: str = ""
    group_id: str = ""


class ConfigUpdateRequest(BaseModel):
    wechat_token: Optional[str] = None
    website_url: Optional[str] = None
    group_id: Optional[str] = None
    new_admin_password: Optional[str] = None


class VariableCreateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = ""


class VariableUpdateRequest(BaseModel):
    value: str
    description: Optional[str] = ""


class LoginRequest(BaseModel):
    pwd: str


class SettingsRequest(BaseModel):
    settings: dict = {}
