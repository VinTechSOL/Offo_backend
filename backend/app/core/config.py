from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ALLOW_DEV_OTP: bool = False
    DEV_MASTER_OTP: str = "123456"

    AWS_REGION : str
    S3_BUCKET: str


    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
