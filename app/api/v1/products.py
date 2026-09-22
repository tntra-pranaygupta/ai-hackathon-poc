from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.product import (
    ProductCreate,
    ProductListQuery,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    service = ProductService(db)
    product = await service.create(payload)
    return product


@router.get("", response_model=ProductListResponse)
async def list_products(
    query: ProductListQuery = Depends(),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    items, total = await service.list(
        query.page, query.page_size, query.name, query.is_active, query.sort_by, query.sort_order
    )
    return ProductListResponse(items=items, total=total, page=query.page, page_size=query.page_size)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    service = ProductService(db)
    product = await service.get_by_id(product_id)
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    service = ProductService(db)
    product = await service.update(product_id, payload)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    service = ProductService(db)
    await service.delete(product_id)
    return Response(status_code=204)
