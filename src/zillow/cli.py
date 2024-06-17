"""Parse Zillow for properties in a given location."""

import argparse
import asyncio

from zillow.parse import InputData, parse_zillow_pages


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
