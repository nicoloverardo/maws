from pydantic import BaseModel, HttpUrl, field_validator


class Product(BaseModel):
    product_id: int
    name: str
    brand: str | None = None
    sku: str | None = None
    product_url: HttpUrl
    image_url: HttpUrl | None = None
    contents: str | None = None

    @field_validator("brand", mode="before")
    @classmethod
    def empty_brand_to_none(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None
