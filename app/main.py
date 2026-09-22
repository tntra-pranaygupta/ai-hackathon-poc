from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.core.exceptions import (
    DuplicateEmailError,
    DuplicateSkuError,
    InvalidCredentialsError,
    NotFoundError,
)

app = FastAPI(title="Ecommerce Management API")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"error": "Validation failed", "details": details})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
        headers=exc.headers,
    )


@app.exception_handler(DuplicateEmailError)
async def duplicate_email_handler(request: Request, exc: DuplicateEmailError):
    return JSONResponse(status_code=409, content={"error": "Email already registered"})


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    return JSONResponse(status_code=401, content={"error": "Invalid credentials"})


@app.exception_handler(DuplicateSkuError)
async def duplicate_sku_handler(request: Request, exc: DuplicateSkuError):
    return JSONResponse(status_code=409, content={"error": "sku already in use"})


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"error": "Resource not found"})
