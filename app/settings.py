from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field("sqlite://", env="INVENTORY_DATABASE_URL")
    low_stock_threshold: int = Field(5, ge=0)
    max_reservation_qty: int = 100
    service_name: str = "inventory"

    class Config:
        env_prefix = "INVENTORY_"
        case_sensitive = False


settings = Settings()
