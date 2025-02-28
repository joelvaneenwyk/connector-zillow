"""Parse Zillow for properties in a given location."""

import argparse
import asyncio
import pathlib
from typing import Any, Dict, List, Optional

import requests
import unicodecsv as csv  # type: ignore
from lxml import html
from playwright.async_api import async_playwright

from zillow.parse import InputData, parse_zillow_pages


def parse(zip_code: str, filter_request: Optional[str] = None) -> List[Dict[str, Any]]:
    """Parse the Zillow website to get the properties we care about.

    Args:
        zip_code (str): _description_
        filter_request (Optional[str], optional): _description_. Defaults to None.

    Returns:
        List[Dict[str, Any]]: _description_
    """
    cookies_path = pathlib.Path().cwd().joinpath("cookie.txt")

    cookies_data = {}  # type: Dict[str, str]
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
            f"https://www.zillow.com/homes/for_sale/{zip_code}/0_singlestory/days_sort"
        )
    elif filter_request == "cheapest":
        url = f"https://www.zillow.com/homes/for_sale/{zip_code}/0_singlestory/pricea_sort/"
    else:
        url = (
            f"https://www.zillow.com/homes/for_sale/{zip_code}_rb/?fromHomePage=true"
            f"&shouldFireSellPageImplicitClaimGA=false&fromHomePageTab=buy "
        )

    for _ in range(5):
        response = requests.request(
            "GET", url, headers={}, data={}, cookies=cookies_data, timeout=5
        )
        print(response.text)
        print(response.status_code)

        parser = html.fromstring(response.text)
        search_results = parser.xpath("//div[@id='search-results']//article")
        properties_list: List[Dict[str, Any]] = []

        if type(search_results) in (
            type(bool),
            type(float),
            type(int),
            type(None),
            type(str),
        ):
            continue

        # assert search_results is list[XPathObject]
        for properties in search_results:
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
            out_properties: Dict[str, Any] = {
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
                properties_list.append(out_properties)

    return properties_list


async def run_zillow_parse(data: InputData) -> None:
    """Parse arguments and start.

    Args:
        zip_code (str): _description_
        sort (str): _description_
    """
    zip_code, sort = data.zip_code, data.sort

    print(f"Fetching data for {zip_code}")
    async with async_playwright() as p:
        browser_type = p.chromium
        browser = await browser_type.launch()
        try:
            # parse(zip_code, browser)
            scraped_data = await parse_zillow_pages(data, browser)
        except Exception:
            print("An error occurred")
            try:
                scraped_data = parse(zip_code, sort)
            except Exception:
                print("Failed backup parse")
                scraped_data = []
            
        finally:
            await browser.close()

    print("Writing data to output file")
    with open(f"properties-{zip_code}.csv", "wb") as csv_file:
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

    asyncio.run(run_zillow_parse(data))
