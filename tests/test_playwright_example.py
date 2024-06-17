import re

from playwright.async_api import Page, expect


async def test_has_title(page: Page):
    await page.goto("https://playwright.dev/")

    # Expect a title "to contain" a substring.
    await expect(page).to_have_title(re.compile("Playwright"))


async def test_get_started_link(page: Page):
    await page.goto("https://playwright.dev/")

    # Click the get started link.
    await page.get_by_role("link", name="Get started").click()

    # Expects page to have a heading with the name of Installation.
    await expect(page.get_by_role("heading", name="Installation")).to_be_visible()
