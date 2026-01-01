from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
