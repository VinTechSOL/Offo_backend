from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ALLOW_DEV_OTP: bool = True
    DEV_MASTER_OTP: str = "123456"
    MSG91_AUTH_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""
    ENVIRONMENT: str = "development"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION : str
    S3_BUCKET: str
    
    PHONEPE_CLIENT_ID: str
    PHONEPE_CLIENT_SECRET: str
    PHONEPE_CLIENT_VERSION: int
    PHONEPE_ENV: str = "SANDBOX"

    PHONEPE_CALLBACK_USERNAME: str
    PHONEPE_CALLBACK_PASSWORD: str

    PHONEPE_REDIRECT_URL: str


    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
