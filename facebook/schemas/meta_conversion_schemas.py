import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MetaCustomData(BaseModel):
    currency: str = Field(default="USD", max_length=3)
    value: float = Field(default=0.0)
    content_ids: Optional[List[str]] = Field(default=None)
    content_type: str = Field(default="product")
    content_name: Optional[str] = None
    num_items: Optional[int] = None
    order_id: Optional[str] = None
    status: Optional[str] = None


class MetaUserData(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    external_id: Optional[str] = None
    client_ip_address: Optional[str] = None
    client_user_agent: Optional[str] = None
    fbp: Optional[str] = None
    fbc: Optional[str] = None

    @field_validator(
        "email", "first_name", "last_name", "city", "state", "country", "external_id"
    )
    @classmethod
    def normalize_string(cls, v):
        return v.strip().lower() if v else v

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v):
        return re.sub(r"\D", "", v) if v else v
