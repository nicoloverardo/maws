import random
from typing import Literal

from pydantic import BaseModel, HttpUrl, computed_field


class Urls(BaseModel):
    base_url: HttpUrl = HttpUrl("https://order.asiaexpressfood.nl")

    base_lang: str = "en"

    list_limit_str: str = "product_list_limit"
    list_limit_value: Literal["48", "144"] = "48"

    rate_limit_seconds: float = 2.0
    timeout: float = 10.0

    products_path: str = "/assortiment.html"

    @computed_field
    @property
    def products_url(self) -> str:
        return self.base_url.build(
            scheme=self.base_url.scheme,
            host=self.base_url.host,
            query=f"{self.list_limit_str}={self.list_limit_value}",
            path=f"{self.base_lang}{self.products_path}",
        ).encoded_string()


class UserAgents(BaseModel):
    ua_list: list[str] = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.10 Safari/605.1.1"
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3"
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Trailer/93.3.8652.5"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0."
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0."
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0."
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0."
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.1958"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136."
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.3"
    ]

    def get_random_ua(self) -> str:
        return random.choice(self.ua_list)

    def get_random_ua_header(self) -> dict[str, str]:
        return {"User-Agent": self.get_random_ua()}


class Config(BaseModel):
    urls: Urls = Urls()
    user_agents: UserAgents = UserAgents()
