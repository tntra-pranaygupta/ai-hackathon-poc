async def get_auth_header(client, email="writer@example.com", password="password123"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def sample_product(**overrides):
    data = {
        "name": "Widget",
        "description": "A useful widget",
        "price": "9.99",
        "sku": "SKU-1",
        "stock_quantity": 10,
        "is_active": True,
    }
    data.update(overrides)
    return data


async def test_create_product_requires_auth(client):
    resp = await client.post("/api/v1/products", json=sample_product())
    assert resp.status_code == 401


async def test_create_product_success(client):
    headers = await get_auth_header(client)
    resp = await client.post("/api/v1/products", json=sample_product(), headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["sku"] == "SKU-1"
    assert "id" in body and "created_at" in body and "updated_at" in body


async def test_create_product_invalid_input_returns_422(client):
    headers = await get_auth_header(client)
    resp = await client.post(
        "/api/v1/products", json=sample_product(price="-1"), headers=headers
    )
    assert resp.status_code == 422

    resp2 = await client.post(
        "/api/v1/products", json=sample_product(stock_quantity=-5), headers=headers
    )
    assert resp2.status_code == 422

    resp3 = await client.post(
        "/api/v1/products", json={"price": "1.00", "sku": "SKU-X"}, headers=headers
    )
    assert resp3.status_code == 422


async def test_create_product_duplicate_sku_returns_409(client):
    headers = await get_auth_header(client)
    await client.post("/api/v1/products", json=sample_product(), headers=headers)
    resp = await client.post("/api/v1/products", json=sample_product(name="Other"), headers=headers)
    assert resp.status_code == 409


async def test_get_product_by_id(client):
    headers = await get_auth_header(client)
    create_resp = await client.post("/api/v1/products", json=sample_product(), headers=headers)
    product_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/products/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["sku"] == "SKU-1"


async def test_get_nonexistent_product_returns_404(client):
    resp = await client.get("/api/v1/products/999999")
    assert resp.status_code == 404


async def test_list_products_pagination_filter_sort(client):
    headers = await get_auth_header(client)
    await client.post("/api/v1/products", json=sample_product(sku="A", name="Alpha", price="5.00", is_active=True), headers=headers)
    await client.post("/api/v1/products", json=sample_product(sku="B", name="Beta", price="15.00", is_active=False), headers=headers)
    await client.post("/api/v1/products", json=sample_product(sku="C", name="Alpha Extra", price="10.00", is_active=True), headers=headers)

    resp = await client.get("/api/v1/products", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2

    resp2 = await client.get("/api/v1/products", params={"name": "Alpha"})
    assert resp2.status_code == 200
    names = [item["name"] for item in resp2.json()["items"]]
    assert all("Alpha" in n for n in names)
    assert len(names) == 2

    resp3 = await client.get("/api/v1/products", params={"is_active": "false"})
    assert resp3.status_code == 200
    assert all(item["is_active"] is False for item in resp3.json()["items"])
    assert resp3.json()["total"] == 1

    resp4 = await client.get(
        "/api/v1/products", params={"sort_by": "price", "sort_order": "asc"}
    )
    prices = [float(item["price"]) for item in resp4.json()["items"]]
    assert prices == sorted(prices)

    resp5 = await client.get(
        "/api/v1/products", params={"sort_by": "price", "sort_order": "desc"}
    )
    prices_desc = [float(item["price"]) for item in resp5.json()["items"]]
    assert prices_desc == sorted(prices_desc, reverse=True)


async def test_list_products_no_auth_required(client):
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200


async def test_update_product_requires_auth(client):
    headers = await get_auth_header(client)
    create_resp = await client.post("/api/v1/products", json=sample_product(), headers=headers)
    product_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/v1/products/{product_id}", json={"price": "20.00"})
    assert resp.status_code == 401


async def test_update_product_success_refreshes_updated_at(client):
    headers = await get_auth_header(client)
    create_resp = await client.post("/api/v1/products", json=sample_product(), headers=headers)
    product = create_resp.json()

    resp = await client.patch(
        f"/api/v1/products/{product['id']}", json={"price": "20.00"}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == "20.00"
    assert body["updated_at"] >= product["updated_at"]


async def test_update_product_invalid_data_returns_422(client):
    headers = await get_auth_header(client)
    create_resp = await client.post("/api/v1/products", json=sample_product(), headers=headers)
    product_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/products/{product_id}", json={"price": "-5.00"}, headers=headers
    )
    assert resp.status_code == 422


async def test_update_product_duplicate_sku_returns_409(client):
    headers = await get_auth_header(client)
    await client.post("/api/v1/products", json=sample_product(sku="SKU-A"), headers=headers)
    create_resp = await client.post(
        "/api/v1/products", json=sample_product(sku="SKU-B", name="Other"), headers=headers
    )
    product_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/products/{product_id}", json={"sku": "SKU-A"}, headers=headers
    )
    assert resp.status_code == 409


async def test_update_nonexistent_product_returns_404(client):
    headers = await get_auth_header(client)
    resp = await client.patch(
        "/api/v1/products/999999", json={"price": "1.00"}, headers=headers
    )
    assert resp.status_code == 404


async def test_delete_product_requires_auth(client):
    headers = await get_auth_header(client)
    create_resp = await client.post("/api/v1/products", json=sample_product(), headers=headers)
    product_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/products/{product_id}")
    assert resp.status_code == 401

    get_resp = await client.get(f"/api/v1/products/{product_id}")
    assert get_resp.status_code == 200


async def test_delete_product_success(client):
    headers = await get_auth_header(client)
    create_resp = await client.post("/api/v1/products", json=sample_product(), headers=headers)
    product_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/products/{product_id}", headers=headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/products/{product_id}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent_product_returns_404(client):
    headers = await get_auth_header(client)
    resp = await client.delete("/api/v1/products/999999", headers=headers)
    assert resp.status_code == 404
