"""Parse Zillow for properties in a given location.
"""

import asyncio
import argparse
from playwright.async_api import async_playwright
from typing import Optional, List, Any, Dict, TYPE_CHECKING
from lxml import html
import unicodecsv as csv
import pathlib

if TYPE_CHECKING:
    from playwright.async_api._generated import Browser


class InputData:
    def __init__(self, zip_code: str, sort: str):
        self.zip_code = zip_code
        self.sort = sort


async def parse(browser: 'Browser', input_data: InputData, filter_request: Optional[str] = None) -> List[Dict[str, Any]]:
    """Given already opened browser and set of input data, parse Zillow sites to scrape the data we need."""

    page = await browser.new_page()

    cookies_path = pathlib.Path().cwd().joinpath("cookie.txt")

    cookies_data = {}
    try:
        with cookies_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                array = line.split("\t")
                key = array.pop(0)
                cookies_data.setdefault(key, array[1])
    except IOError:
        print("Cookie file not found. Please log in and save the cookies to continue")

    if filter_request == "newest":
        url = (
            f"https://www.zillow.com/homes/for_sale/{input_data.zip_code}/0_singlestory/days_sort"
        )
    elif filter_request == "cheapest":
        url = f"https://www.zillow.com/homes/for_sale/{input_data.zip_code}/0_singlestory/pricea_sort/"
    else:
        url = (
            f"https://www.zillow.com/homes/for_sale/{input_data.zip_code}_rb/?fromHomePage=true"
            f"&shouldFireSellPageImplicitClaimGA=false&fromHomePageTab=buy "
        )

    properties_list: List[Dict[str, Any]] = []
    for i in range(5):
        await page.goto(url)
        page_data = await page.content()
        await page.screenshot(path=f"example-{i}.png")
        print(f"Fetching data for {input_data.zip_code}")
        print(page_data)
        # print(response.status_code)

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
            raw_price = properties.xpath(
                ".//span[@class='zsg-photo-card-price']//text()"
            )
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

    return properties_list


async def parse_zillow_pages(input_data: InputData):
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch()
            try:
                scraped_data = await parse(browser, input_data)
                print("Writing data to output file")
                with open(f"properties-{input_data.zip_code}.csv", "wb") as csv_file:
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
                    for row in scraped_data:
                        writer.writerow(row)
            finally:
                await browser.close()


def main() -> None:
    """Parse arguments and start.

    Args:
        zip_code (str): _description_
        sort (str): _description_
    """
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    argparser.add_argument("zipcode", help="Enter the zip code")
    argparser.add_argument(
        "sort",
        nargs="?",
        help="""available sort orders are :
        newest : Latest property details,
        cheapest : Properties with cheapest price""",
        default="homes for you",
        choices=["newest", "cheapest"],
    )
    args = argparser.parse_args()
    data = InputData(args.zipcode, args.sort)
    asyncio.run(parse_zillow_pages(data))
