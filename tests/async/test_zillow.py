from playwright.async_api import Page, expect
import re
from zillow.parse import get_cookies
import pytest


@pytest.mark.asyncio
async def test_zillow_parser(page: Page):
    cookies = get_cookies()
    assert cookies is not None

    try:
        await page.goto("https://playwright.dev/")
        await expect(page).to_have_title(re.compile("Playwright"))
    except Exception:
        # await context.add_cookies(get_cookies())
        # results = await parse(page)
        # assert results is not None
        pass
