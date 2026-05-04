from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, Any

T = TypeVar("T")

class ResponseModel(BaseModel, Generic[T]):
    status: str = "success"
    data: Optional[T] = None
    message: str = ""

class PaginatedMeta(BaseModel):
    total: int
    page: int
    limit: int

class PaginatedResponseModel(BaseModel, Generic[T]):
    status: str = "success"
    data: T
    meta: PaginatedMeta
    message: str = ""
