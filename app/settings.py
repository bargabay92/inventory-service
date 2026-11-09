from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field("sqlite://", validation_alias="INVENTORY_DATABASE_URL")
    low_stock_threshold: int = Field(5, ge=0)
    max_reservation_qty: int = 100
    service_name: str = "inventory"
    model_config = SettingsConfigDict(env_prefix="INVENTORY_", case_sensitive=False)


settings = Settings()
