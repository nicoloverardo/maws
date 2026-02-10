from pydantic import BaseModel, HttpUrl, field_validator


class Product(BaseModel):
    product_id: int
    name: str
    brand: str | None = None
    sku: str | None = None
    product_url: HttpUrl
    image_url: HttpUrl | None = None
    contents: str | None = None

    price: str | None = None
    tier_price: str | None = None
    best_before: str | None = None
    stock_status: str | None = None

    # Detailed product information
    categories: list[str] | None = None
    description: str | None = None
    stock_available: bool | None = None
    price_tiers: list[dict] | None = None
    specifications: dict | None = None

    @field_validator("brand", mode="before")
    @classmethod
    def empty_brand_to_none(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None
