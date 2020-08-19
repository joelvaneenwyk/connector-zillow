"""
Main Executor
"""
from typing import Optional, List, Any, Dict

from lxml import html
import requests
import unicodecsv as csv
import argparse
import pathlib
import sys

def parse(zip_code: str, filter_request: Optional[str] = None) -> List[Dict[str, Any]]:
    
    cookies_path = pathlib.Path().cwd().joinpath('cookie.txt')

    cookies_data = {}
    with cookies_path.open() as fp:
        for line in fp:
            array = line.split('\t')
            key = array.pop(0)
            cookies_data.setdefault(key, array[1])

    if filter_request == "newest":
        url = f"https://www.zillow.com/homes/for_sale/{zip_code}/0_singlestory/days_sort"
    elif filter_request == "cheapest":
        url = f"https://www.zillow.com/homes/for_sale/{zip_code}/0_singlestory/pricea_sort/"
    else:
        url = f"https://www.zillow.com/homes/for_sale/{zip_code}_rb/?fromHomePage=true" \
              f"&shouldFireSellPageImplicitClaimGA=false&fromHomePageTab=buy "

    for i in range(5):
        response = requests.request("GET", url, headers={}, data={}, cookies=cookies_data)
        print(response.text)
        print(response.status_code)

        parser = html.fromstring(response.text)
        search_results = parser.xpath("//div[@id='search-results']//article")
        properties_list: List[Dict[str, Any]] = []

        for properties in search_results:
            raw_address = properties.xpath(".//span[@itemprop='address']//span[@itemprop='streetAddress']//text()")
            raw_city = properties.xpath(".//span[@itemprop='address']//span[@itemprop='addressLocality']//text()")
            raw_state = properties.xpath(".//span[@itemprop='address']//span[@itemprop='addressRegion']//text()")
            raw_postal_code = properties.xpath(".//span[@itemprop='address']//span[@itemprop='postalCode']//text()")
            raw_price = properties.xpath(".//span[@class='zsg-photo-card-price']//text()")
            raw_info = properties.xpath(".//span[@class='zsg-photo-card-info']//text()")
            raw_broker_name = properties.xpath(".//span[@class='zsg-photo-card-broker-name']//text()")
            url = properties.xpath(".//a[contains(@class,'overlay-link')]/@href")
            raw_title = properties.xpath(".//h4//text()")

            address = ' '.join(' '.join(raw_address).split()) if raw_address else None
            city = ''.join(raw_city).strip() if raw_city else None
            state = ''.join(raw_state).strip() if raw_state else None
            postal_code = ''.join(raw_postal_code).strip() if raw_postal_code else None
            price = ''.join(raw_price).strip() if raw_price else None
            info = ' '.join(' '.join(raw_info).split()).replace(u"\xb7", ',')
            broker = ''.join(raw_broker_name).strip() if raw_broker_name else None
            title = ''.join(raw_title) if raw_title else None
            property_url = 'https://www.zillow.com' + url[0] if url else None
            is_for_sale = properties.xpath('.//span[@class="zsg-icon-for-sale"]')
            properties: Dict[str, Any] = {
                'address': address,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'price': price,
                'facts and features': info,
                'real estate provider': broker,
                'url': property_url,
                'title': title
            }
            if is_for_sale:
                properties_list.append(properties)

        return properties_list


def main(zip_code: str, sort: str) -> None:
    print(f"Fetching data for {zip_code}")
    scraped_data = parse(zip_code, sort)
    print("Writing data to output file")
    with open(F"properties-{zip_code}.csv", 'wb')as csv_file:
        fieldnames = ['title', 'address', 'city', 'state', 'postal_code', 'price', 'facts and features',
                      'real estate provider', 'url']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in scraped_data:
            writer.writerow(row)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    argparser.add_argument(
        'zipcode',
        help='Enter the zip code'
    )
    argparser.add_argument(
        'sort',
        nargs='?',
        help="""available sort orders are :
        newest : Latest property details,
        cheapest : Properties with cheapest price""",
        default='homes for you',
        choices=['newest', 'cheapest']
    )
    args = argparser.parse_args()
    main(args.zipcode, args.sort)
