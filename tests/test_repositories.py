import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository


async def test_user_repository_create_and_get_by_email_roundtrip(db_session):
    repo = UserRepository(db_session)
    created = await repo.create(email="repo@example.com", password_hash="hash")
    fetched = await repo.get_by_email("repo@example.com")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "repo@example.com"


async def test_user_repository_duplicate_email_raises_integrity_error(db_session):
    repo = UserRepository(db_session)
    await repo.create(email="dup@example.com", password_hash="hash1")
    with pytest.raises(IntegrityError):
        await repo.create(email="dup@example.com", password_hash="hash2")


async def test_product_repository_create_get_and_delete(db_session):
    repo = ProductRepository(db_session)
    product = await repo.create(
        name="Repo Widget", description=None, price=1.5, sku="REPO-1",
        stock_quantity=5, is_active=True,
    )
    fetched = await repo.get_by_id(product.id)
    assert fetched is not None
    assert fetched.sku == "REPO-1"

    by_sku = await repo.get_by_sku("REPO-1")
    assert by_sku is not None and by_sku.id == product.id

    await repo.delete(fetched)
    assert await repo.get_by_id(product.id) is None


async def test_product_repository_duplicate_sku_raises_integrity_error(db_session):
    repo = ProductRepository(db_session)
    await repo.create(
        name="First", description=None, price=1.0, sku="DUP-SKU",
        stock_quantity=0, is_active=True,
    )
    with pytest.raises(IntegrityError):
        await repo.create(
            name="Second", description=None, price=2.0, sku="DUP-SKU",
            stock_quantity=0, is_active=True,
        )


async def test_product_repository_list_pagination_filter_sort(db_session):
    repo = ProductRepository(db_session)
    await repo.create(name="Zeta", description=None, price=30, sku="Z1", stock_quantity=1, is_active=True)
    await repo.create(name="Alpha", description=None, price=10, sku="A1", stock_quantity=1, is_active=True)
    await repo.create(name="Beta", description=None, price=20, sku="B1", stock_quantity=1, is_active=False)

    items, total = await repo.list(1, 2, None, None, "created_at", "asc")
    assert total == 3
    assert len(items) == 2

    items_active, total_active = await repo.list(1, 100, None, True, "created_at", "asc")
    assert total_active == 2

    items_sorted, _ = await repo.list(1, 100, None, None, "price", "asc")
    prices = [float(p.price) for p in items_sorted]
    assert prices == sorted(prices)


async def test_product_repository_list_name_filter_escapes_like_wildcards(db_session):
    repo = ProductRepository(db_session)
    await repo.create(name="100% Cotton", description=None, price=5, sku="W1", stock_quantity=1, is_active=True)
    await repo.create(name="100 Pure Wool", description=None, price=5, sku="W2", stock_quantity=1, is_active=True)

    items, total = await repo.list(1, 100, "100%", None, "created_at", "asc")
    assert total == 1
    assert items[0].name == "100% Cotton"
