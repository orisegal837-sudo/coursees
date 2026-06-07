import html
from ddgs import DDGS
import aiohttp
import asyncio
import sys
from bs4 import BeautifulSoup
import random
from curl_cffi.requests import AsyncSession
sys.stdout.reconfigure(encoding='utf-8')

def parse_html_content(html_content: str) -> str:
    """Parses HTML and extracts text, removing unwanted tags."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for unwanted_tag in soup(['script', 'style', 'noscript','nav','footer', 'header']):
        unwanted_tag.decompose()
    return soup.get_text(separator=' ', strip=True)

def get_urls(query, max_results=10):
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        # Extract just the URLs from the result dictionaries
        urls = [result['href'] for result in results]
        return urls

        
async def extract_multiple_urls(urls: list[str] ):
        """extracts multiple urls with one aiohttp session"""

        articles = []
        headers = headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
        print("Starting batch extraction...")
        tasks = [extract_page(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result['status'] == 'success':
                articles.append(result.content)
            else:
                print(f"Failed to extract {result.get('url')}: {result.get('error')}")            
        return articles
async def extract_page( url: str):
    """Worker function: Fetches a single URL and extracts ALL readable text with edge-case handling."""
    if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return {"url": url, "status": "failed", "error": "Invalid or empty URL"}

    try:
        async with AsyncSession(impersonate="chrome120") as session :
            response = await session.get(url, timeout=15)
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and content_type:
                return {"url": url, "status": "failed", "error": f"Unsupported content type: {content_type}"}

            # 3. Fixed Status Check: Do not allow 403s to pass through
            print(f'URL: {url} Status Code: {response.status_code}')
            if response.status_code != 200:
                return {"url": url, "status": "failed", "error": f"HTTP {response.status_code}: {response.reason}"}

            html = response.text


            if 'text/plain' in content_type:
                full_text = html
            else:
                # Assuming parse_html_content is defined elsewhere in your file
                full_text = await asyncio.to_thread(parse_html_content, html)
            
            if not full_text or not full_text.strip():
                return {"url": url, "status": "failed", "error": "No readable text content found"}

            return {"url": url, "status": "success", "full text": full_text.strip()}

    except asyncio.TimeoutError:
        return {"url": url, "status": "failed", "error": "Request timed out"}
    except aiohttp.ClientConnectorError as e:
        return {"url": url, "status": "failed", "error": f"Connection failed: {str(e)}"}
    except aiohttp.ClientError as e:
        return {"url": url, "status": "failed", "error": f"Client error: {str(e)}"}
    except Exception as e:
        return {"url": url, "status": "failed", "error": f"Unexpected error: {str(e)}"}

print(get_urls("Microscopy of Lignin Removal and Cellulose Exposure (SEM, AFM, Confocal)"))

async def main():
    links = get_urls("Microscopy of Lignin Removal and Cellulose Exposure (SEM, AFM, Confocal)")
    articles = await extract_multiple_urls(links)
    print(articles)

if __name__ == '__main__': 
    asyncio.run(main())
