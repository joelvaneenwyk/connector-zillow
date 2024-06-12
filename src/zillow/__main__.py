"""
Main Executor
"""

from .cli import main
import argparse


if __name__ == "__main__":
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
    main(args.zipcode, args.sort)
