from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    price: Decimal = Field(gt=0)
    sku: str = Field(min_length=1, max_length=64)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    sku: str
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    name: str | None = None
    is_active: bool | None = None
    sort_by: Literal["price", "created_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
