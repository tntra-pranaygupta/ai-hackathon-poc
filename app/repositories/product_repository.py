from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **fields) -> Product:
        # Flush (not commit) — the service layer owns the transaction
        # boundary so it can coordinate multiple repository calls in one
        # unit of work as the app grows.
        product = Product(**fields)
        self.session.add(product)
        await self.session.flush()
        return product

    async def get_by_id(self, product_id: int) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int,
        page_size: int,
        name: str | None,
        is_active: bool | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Product], int]:
        filters = []
        if name:
            # Escape LIKE metacharacters in user input so a literal "%" or
            # "_" in the search term is matched literally, not as a wildcard.
            escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            filters.append(Product.name.ilike(f"%{escaped}%", escape="\\"))
        if is_active is not None:
            filters.append(Product.is_active == is_active)

        base_stmt = select(Product)
        count_stmt = select(func.count()).select_from(Product)
        for f in filters:
            base_stmt = base_stmt.where(f)
            count_stmt = count_stmt.where(f)

        sort_column = Product.price if sort_by == "price" else Product.created_at
        order_fn = asc if sort_order == "asc" else desc
        base_stmt = base_stmt.order_by(order_fn(sort_column))
        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)

        items_result = await self.session.execute(base_stmt)
        total_result = await self.session.execute(count_stmt)

        items = list(items_result.scalars().all())
        total = total_result.scalar_one()
        return items, total

    async def update(self, product: Product, fields: dict) -> Product:
        for key, value in fields.items():
            setattr(product, key, value)
        await self.session.flush()
        return product

    async def delete(self, product: Product) -> None:
        await self.session.delete(product)
        await self.session.flush()
