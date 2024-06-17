"""Parse Zillow for properties in a given location."""

import argparse
import asyncio

from zillow.parse import InputData, parse_zillow_pages
from playwright.async_api import async_playwright


async def run_zillow_parse(input_data: InputData):
    async with async_playwright() as p:
        browser_type = p.chromium
        browser = await browser_type.launch()
        try:
            await parse_zillow_pages(input_data, browser)
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

    asyncio.run(run_zillow_parse(data))
