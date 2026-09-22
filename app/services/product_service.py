from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateSkuError, NotFoundError
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProductRepository(session)

    async def create(self, data: ProductCreate) -> Product:
        existing = await self.repo.get_by_sku(data.sku)
        if existing is not None:
            raise DuplicateSkuError()
        try:
            product = await self.repo.create(**data.model_dump())
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateSkuError()
        await self.session.refresh(product)
        return product

    async def list(
        self,
        page: int,
        page_size: int,
        name: str | None,
        is_active: bool | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Product], int]:
        return await self.repo.list(page, page_size, name, is_active, sort_by, sort_order)

    async def get_by_id(self, product_id: int) -> Product:
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError()
        return product

    async def update(self, product_id: int, data: ProductUpdate) -> Product:
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError()

        fields = data.model_dump(exclude_unset=True)
        if "sku" in fields and fields["sku"] != product.sku:
            conflicting = await self.repo.get_by_sku(fields["sku"])
            if conflicting is not None:
                raise DuplicateSkuError()

        try:
            updated = await self.repo.update(product, fields)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateSkuError()
        await self.session.refresh(updated)
        return updated

    async def delete(self, product_id: int) -> None:
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError()
        await self.repo.delete(product)
        await self.session.commit()
