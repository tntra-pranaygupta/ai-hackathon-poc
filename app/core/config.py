import os


class Settings:
    """Application settings sourced from environment variables only."""

    def __init__(self) -> None:
        self.database_url: str = self._require("DATABASE_URL")
        self.jwt_secret_key: str = self._require("JWT_SECRET_KEY")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_access_token_expire_minutes: int = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )

    @staticmethod
    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Required environment variable {name} is not set")
        return value


settings = Settings()
