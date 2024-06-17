"""Parse Zillow for properties in a given location."""

import json
import pathlib
from typing import Any, Dict, List, Optional, Sequence

import unicodecsv as csv
from lxml import html
from playwright._impl._api_structures import SetCookieParam
from playwright.async_api import Page, async_playwright


class InputData:
    def __init__(self, zip_code: str = "94105", sort: str = "nearest"):
        self.zip_code = zip_code
        self.sort = sort


def get_cookies() -> Sequence[SetCookieParam]:
    cookie_data_list: Sequence[SetCookieParam] = []
    root = pathlib.Path().cwd()
    pyproject = None
    while root is not None:
        pyproject = root.joinpath("pyproject.toml")
        if pyproject.exists():
            root = None

    if pyproject is not None:
        project_intermediate_path = pyproject.parent.joinpath(".build")
        project_intermediate_path.mkdir(exist_ok=True, parents=True)
        cookies_path = project_intermediate_path.joinpath("cookies.json")
        try:
            with cookies_path.open("r", encoding="utf-8") as fp:
                cookie_raw_data = json.load(fp)
                if isinstance(cookie_raw_data, list):
                    for cookie in cookie_raw_data:
                        name = cookie.get("name") or cookie.get("domain") or "other"
                        cookie["name"] = name
                        cookie_data_list.append(SetCookieParam(**cookie))
        except IOError:
            print(
                "Cookie file not found. Please log in and save the cookies to continue"
            )
    return cookie_data_list


async def parse(
    page: Page,
    input_data: Optional[InputData] = None,
    filter_request: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Given already opened browser and set of input data, parse Zillow sites to scrape the data we need."""

    data = input_data or InputData()
    if filter_request == "newest":
        url = f"https://www.zillow.com/homes/for_sale/{data.zip_code}/0_singlestory/days_sort"
    elif filter_request == "cheapest":
        url = f"https://www.zillow.com/homes/for_sale/{data.zip_code}/0_singlestory/pricea_sort/"
    else:
        url = (
            f"https://www.zillow.com/homes/for_sale/{data.zip_code}_rb/?fromHomePage=true"
            f"&shouldFireSellPageImplicitClaimGA=false&fromHomePageTab=buy "
        )

    properties_list: List[Dict[str, Any]] = []

    await page.goto(url)
    page_data = await page.content()
    await page.screenshot(path="example.png")
    print(f"Fetching data for {data.zip_code}")
    print(page_data)

    parser = html.fromstring(page_data)
    search_results = parser.xpath("//div[@id='search-results']//article")

    for properties in search_results:
        if not isinstance(properties, html.HtmlElement):
            continue

        raw_address = properties.xpath(
            ".//span[@itemprop='address']//span[@itemprop='streetAddress']//text()"
        )
        raw_city = properties.xpath(
            ".//span[@itemprop='address']//span[@itemprop='addressLocality']//text()"
        )
        raw_state = properties.xpath(
            ".//span[@itemprop='address']//span[@itemprop='addressRegion']//text()"
        )
        raw_postal_code = properties.xpath(
            ".//span[@itemprop='address']//span[@itemprop='postalCode']//text()"
        )
        raw_price = properties.xpath(".//span[@class='zsg-photo-card-price']//text()")
        raw_info = properties.xpath(".//span[@class='zsg-photo-card-info']//text()")
        raw_broker_name = properties.xpath(
            ".//span[@class='zsg-photo-card-broker-name']//text()"
        )
        url = properties.xpath(".//a[contains(@class,'overlay-link')]/@href")
        raw_title = properties.xpath(".//h4//text()")

        address = " ".join(" ".join(raw_address).split()) if raw_address else None
        city = "".join(raw_city).strip() if raw_city else None
        state = "".join(raw_state).strip() if raw_state else None
        postal_code = "".join(raw_postal_code).strip() if raw_postal_code else None
        price = "".join(raw_price).strip() if raw_price else None
        info = " ".join(" ".join(raw_info).split()).replace("\xb7", ",")
        broker = "".join(raw_broker_name).strip() if raw_broker_name else None
        title = "".join(raw_title) if raw_title else None
        property_url = "https://www.zillow.com" + url[0] if url else None
        is_for_sale = properties.xpath('.//span[@class="zsg-icon-for-sale"]')
        properties: Dict[str, Any] = {
            "address": address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "price": price,
            "facts and features": info,
            "real estate provider": broker,
            "url": property_url,
            "title": title,
        }
        if is_for_sale:
            properties_list.append(properties)

    print("Writing data to output file")
    with open(f"properties-{data.zip_code}.csv", "wb") as csv_file:
        fieldnames = [
            "title",
            "address",
            "city",
            "state",
            "postal_code",
            "price",
            "facts and features",
            "real estate provider",
            "url",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in properties_list:
            writer.writerow(row)

    return properties_list


async def parse_zillow_pages(input_data: InputData):
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch()
            try:
                page = await browser.new_page()
                await page.context.clear_cookies()
                await page.context.add_cookies(get_cookies())
                await parse(page, input_data)
            finally:
                await browser.close()
