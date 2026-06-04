from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/dms"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme"

    class Config:
        env_file = ".env"


settings = Settings()
