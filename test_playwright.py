import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await stealth_async(page)
        
        print("Navigating...")
        response = await page.goto('https://www.science.org/doi/10.1126/science.1260088', wait_until='domcontentloaded')
        print(f"Status: {response.status}")
        
        await page.wait_for_timeout(3000) # Give it 3 seconds for CF to redirect if any
        content = await page.content()
        print(f"Content snippet: {content[:200]}")
        
        await browser.close()

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
