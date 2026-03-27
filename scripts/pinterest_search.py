import re
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class PinterestSearcher:
    """Search Pinterest and return image URLs."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def search(self, query: str, num_images: int = 20) -> list[str]:
        """
        Search Pinterest and return image URLs.

        Args:
            query: Search term
            num_images: Number of image URLs to return

        Returns:
            List of image URLs
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

                            high_res = re.sub(r'/\d+x\d*/', '/736x/', src)

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
        return image_urls


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Search Pinterest and print image URLs")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-n", "--num", type=int, default=20, help="Number of images (default: 20)")
    parser.add_argument("--show-browser", action="store_true", help="Show browser window")

    args = parser.parse_args()

    searcher = PinterestSearcher(headless=not args.show_browser)
    urls = searcher.search(args.query, args.num)

    print("\nImage URLs:")
    for url in urls:
        print(url)


if __name__ == "__main__":
    main()
