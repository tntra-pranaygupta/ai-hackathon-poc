#!/usr/bin/env bash
# Docker Compose smoke check (product-crud T007).
#
# Proves that on a machine with no host-installed PostgreSQL, `docker compose
# up --build` brings up the full stack and both the /api/v1/auth and
# /api/v1/products routers work end to end.
#
# Usage: ./scripts/smoke_check.sh   (run from the repo root)
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== docker compose up --build =="
docker compose up --build -d

cleanup() {
  echo "== docker compose down -v =="
  docker compose down -v
}
trap cleanup EXIT

echo "== waiting for api to become healthy =="
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null; then
    break
  fi
  sleep 1
done
curl -sf http://localhost:8000/health
echo
echo "health check OK"

EMAIL="smoke-$(date +%s)@example.com"

echo "== POST /api/v1/auth/register =="
REGISTER_STATUS=$(curl -sS -o /tmp/register.json -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"password123\"}")
[ "$REGISTER_STATUS" = "201" ] || { echo "register failed: $REGISTER_STATUS"; cat /tmp/register.json; exit 1; }
echo "register OK"

echo "== POST /api/v1/auth/login =="
TOKEN=$(curl -sS -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"password123\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
[ -n "$TOKEN" ] || { echo "login failed to return a token"; exit 1; }
echo "login OK"

echo "== POST /api/v1/products without auth (expect 401) =="
NO_AUTH_STATUS=$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Smoke Widget","price":"9.99","sku":"SMOKE-CHECK-1"}')
[ "$NO_AUTH_STATUS" = "401" ] || { echo "expected 401, got $NO_AUTH_STATUS"; exit 1; }
echo "unauthenticated create correctly rejected"

echo "== POST /api/v1/products with auth =="
CREATE_STATUS=$(curl -sS -o /tmp/create.json -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Smoke Widget","price":"9.99","sku":"SMOKE-CHECK-1"}')
[ "$CREATE_STATUS" = "201" ] || { echo "create failed: $CREATE_STATUS"; cat /tmp/create.json; exit 1; }
echo "authenticated create OK"

echo "== GET /api/v1/products (no auth) =="
LIST_STATUS=$(curl -sS -o /tmp/list.json -w "%{http_code}" http://localhost:8000/api/v1/products)
[ "$LIST_STATUS" = "200" ] || { echo "list failed: $LIST_STATUS"; cat /tmp/list.json; exit 1; }
echo "public list OK"

echo
echo "SMOKE CHECK PASSED"
