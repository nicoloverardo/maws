from pydantic import HttpUrl, computed_field, BaseModel


class Urls(BaseModel):
    base_url: HttpUrl = HttpUrl("https://order.asiaexpressfood.nl")

    base_lang: str = "en"

    list_limit_query: str = "product_list_limit=144"

    fresh_products_path: str = "/assortiment/fresh-products.html"
    preserved_products_path: str = "/assortiment/preserved-products.html"

    @computed_field
    @property
    def fresh_products_url(self) -> str:
        return self.base_url.build(
            scheme=self.base_url.scheme,
            host=self.base_url.host,
            query=self.list_limit_query,
            path=f"{self.base_lang}{self.fresh_products_path}",
        ).encoded_string()
    
    @computed_field
    @property
    def preserved_products_url(self) -> str:
        return self.base_url.build(
            scheme=self.base_url.scheme,
            host=self.base_url.host,
            query=self.list_limit_query,
            path=f"{self.base_lang}{self.preserved_products_path}",
        ).encoded_string()
