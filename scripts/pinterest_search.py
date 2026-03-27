import os
import re
import time
import requests
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class PinterestDownloader:
    """Download images from Pinterest search results using browser automation."""

    def __init__(self, output_dir: str = "data/pinterest_images", headless: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless

    def search_and_download(self, query: str, num_images: int = 20) -> list[str]:
        """
        Search Pinterest and download images.

        Args:
            query: Search term
            num_images: Number of images to download

        Returns:
            List of downloaded file paths
        """
        image_urls = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                search_url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
                print(f"Searching: {search_url}")

                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

                try:
                    page.wait_for_selector("img[src*='pinimg.com']", timeout=15000)
                except PlaywrightTimeout:
                    print("Waiting longer for images to load...")
                    time.sleep(5)

                time.sleep(3)

                scroll_count = 0
                max_scrolls = max((num_images // 20) + 3, 5)

                while len(image_urls) < num_images and scroll_count < max_scrolls:
                    images = page.query_selector_all("img[src*='pinimg.com']")

                    for img in images:
                        src = img.get_attribute("src")
                        if src and "pinimg.com" in src:
                            if any(x in src for x in ["/75x75_", "/60x60/", "/30x30/", "avatars", "user/"]):
                                continue

                            high_res = self._get_high_res_url(src)

                            if high_res not in image_urls:
                                image_urls.append(high_res)

                            if len(image_urls) >= num_images:
                                break

                    print(f"Found {len(image_urls)} images...")

                    if len(image_urls) >= num_images:
                        break

                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(1.5)
                    scroll_count += 1

            except PlaywrightTimeout as e:
                print(f"Timeout error: {e}")
            except Exception as e:
                print(f"Error during search: {e}")
            finally:
                browser.close()

        image_urls = image_urls[:num_images]
        print(f"\nFound {len(image_urls)} unique images for query: '{query}'")

        prefix = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:30]
        return self._download_images(image_urls, prefix)

    def _get_high_res_url(self, url: str) -> str:
        """Convert thumbnail URL to higher resolution."""
        return re.sub(r'/\d+x\d*/', '/736x/', url)

    def _download_images(self, urls: list[str], prefix: str) -> list[str]:
        """Download images from URLs and save to local directory."""
        downloaded = []

        http_session = requests.Session()
        http_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

        for i, url in enumerate(urls, 1):
            ext = ".jpg"
            if ".png" in url.lower():
                ext = ".png"
            elif ".gif" in url.lower():
                ext = ".gif"
            elif ".webp" in url.lower():
                ext = ".webp"

            filename = f"{prefix}_{i:03d}{ext}"
            filepath = self.output_dir / filename

            try:
                response = http_session.get(url, timeout=30)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(response.content)

                width, height = None, None
                try:
                    with Image.open(filepath) as img:
                        width, height = img.size
                except Exception:
                    pass

                downloaded.append(str(filepath))
                print(f"Downloaded: {filename} ({width}x{height}, {len(response.content) // 1024}KB)")

            except requests.RequestException as e:
                print(f"Failed to download {url}: {e}")

        print(f"Downloaded {len(downloaded)} images to: {self.output_dir}")
        return downloaded


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Download images from Pinterest")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-n", "--num", type=int, default=20, help="Number of images (default: 20)")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: data/pinterest_images/<query>)")
    parser.add_argument("--show-browser", action="store_true", help="Show browser window")

    args = parser.parse_args()

    if args.output is None:
        clean_query = re.sub(r'[^\w\s-]', '', args.query).strip().replace(' ', '_')
        args.output = f"data/pinterest_images/{clean_query}"

    downloader = PinterestDownloader(
        output_dir=args.output,
        headless=not args.show_browser,
    )
    downloaded = downloader.search_and_download(args.query, args.num)

    print(f"\nTotal downloaded: {len(downloaded)} images")


if __name__ == "__main__":
    main()
