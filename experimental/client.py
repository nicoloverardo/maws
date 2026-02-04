import httpx

from maws.urls import Urls

from bs4 import BeautifulSoup

urls = Urls()

client = httpx.Client(follow_redirects=True)

resp = client.get(urls.fresh_products_url)

soup = BeautifulSoup(resp.text, "lxml")

print(soup.select("ol"))
