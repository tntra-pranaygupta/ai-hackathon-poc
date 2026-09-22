class DuplicateEmailError(Exception):
    """Raised when registering with an email that is already in use."""


class InvalidCredentialsError(Exception):
    """Raised on login when credentials are wrong or the user does not exist."""


class DuplicateSkuError(Exception):
    """Raised when creating/updating a product with a sku already in use."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""
