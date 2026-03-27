import os
import re
import time
import requests
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, LargeBinary, Boolean, Text, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()


Base = declarative_base()



class PinterestImage(Base):
    """Stores Pinterest images with binary data."""
    __tablename__ = "pinterest_images"
    
    image_id = Column(Integer, primary_key=True, index=True)
    image_data = Column(LargeBinary, nullable=False)  # Binary image data
    filename = Column(String)                         # Original filename
    mime_type = Column(String)                        # e.g., image/jpeg, image/png
    search_query = Column(String, index=True)         # Query used to find this image
    source_url = Column(String)                       # Original Pinterest URL
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)                       # Size in bytes
    created_at = Column(DateTime, default=datetime.utcnow)



class PinterestDownloader:
    """Download images from Pinterest search results using browser automation."""
    
    def __init__(self, output_dir: str = "data/pinterest_images", headless: bool = True, save_to_db: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.save_to_db = save_to_db
        
        if save_to_db:
            # Create tables if they don't exist
            Base.metadata.create_all(bind=engine)
    
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
                # Navigate to Pinterest search
                search_url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
                print(f"Searching: {search_url}")
                
                # Use domcontentloaded instead of networkidle (faster, more reliable)
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for images to load
                try:
                    page.wait_for_selector("img[src*='pinimg.com']", timeout=15000)
                except PlaywrightTimeout:
                    print("Waiting longer for images to load...")
                    time.sleep(5)
                
                time.sleep(3)  # Let more images load
                
                # Scroll to load more images
                scroll_count = 0
                max_scrolls = max((num_images // 20) + 3, 5)  # At least 5 scrolls
                
                while len(image_urls) < num_images and scroll_count < max_scrolls:
                    # Extract image URLs
                    images = page.query_selector_all("img[src*='pinimg.com']")
                    
                    for img in images:
                        src = img.get_attribute("src")
                        if src and "pinimg.com" in src:
                            # Skip small thumbnails, avatars, and icons
                            if any(x in src for x in ["/75x75_", "/60x60/", "/30x30/", "avatars", "user/"]):
                                continue
                            
                            # Try to get higher resolution version
                            high_res = self._get_high_res_url(src)
                            
                            if high_res not in image_urls:
                                image_urls.append(high_res)
                            
                            if len(image_urls) >= num_images:
                                break
                    
                    print(f"Found {len(image_urls)} images...")
                    
                    if len(image_urls) >= num_images:
                        break
                    
                    # Scroll down
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(1.5)
                    scroll_count += 1
                
            except PlaywrightTimeout as e:
                print(f"Timeout error: {e}")
            except Exception as e:
                print(f"Error during search: {e}")
            finally:
                browser.close()
        
        # Limit to requested number
        image_urls = image_urls[:num_images]
        print(f"\nFound {len(image_urls)} unique images for query: '{query}'")
        
        # Download images
        prefix = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:30]
        print(image_urls)
        return self._download_images(image_urls, prefix, query)
    
    def _get_high_res_url(self, url: str) -> str:
        """Convert thumbnail URL to higher resolution."""
        # Pinterest URL patterns: /60x60/, /75x75/, /236x/, /474x/, /564x/, /736x/, /originals/
        # Use regex to match any size pattern and replace with 736x
        high_res = re.sub(r'/\d+x\d*/', '/736x/', url)
        return high_res
    
    def _download_images(self, urls: list[str], prefix: str, query: str) -> list[str]:
        """Download images from URLs and save binary data to database."""
        downloaded = []
        db_session = session() if self.save_to_db else None
        
        http_session = requests.Session()
        http_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        
        # MIME type mapping
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        
        try:
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
                    
                    # Get binary data
                    image_data = response.content
                    file_size = len(image_data)
                    
                    # Save to local file
                    with open(filepath, "wb") as f:
                        f.write(image_data)
                    
                    # Get image dimensions
                    width, height = None, None
                    try:
                        with Image.open(filepath) as img:
                            width, height = img.size
                    except Exception:
                        pass
                    
                    downloaded.append(str(filepath))
                    print(f"Downloaded: {filename} ({width}x{height}, {file_size // 1024}KB)")
                    
                    # Save binary data to database
                    if db_session:
                        db_image = PinterestImage(
                            image_data=image_data,
                            filename=filename,
                            mime_type=mime_types.get(ext, "image/jpeg"),
                            search_query=query,
                            source_url=url,
                            width=width,
                            height=height,
                            file_size=file_size
                        )
                        db_session.add(db_image)
                    
                except requests.RequestException as e:
                    print(f"Failed to download {url}: {e}")
            
            # Commit all to database
            if db_session:
                db_session.commit()
                print(f"\nSaved {len(downloaded)} images (binary) to database")
                
        finally:
            if db_session:
                db_session.close()
        
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
    parser.add_argument("--no-db", action="store_true", help="Don't save to database")
    
    args = parser.parse_args()
    
    # Set default output directory based on query
    if args.output is None:
        clean_query = re.sub(r'[^\w\s-]', '', args.query).strip().replace(' ', '_')
        args.output = f"data/pinterest_images/{clean_query}"    
    
    downloader = PinterestDownloader(
        output_dir=args.output,
        headless=not args.show_browser,
        save_to_db=not args.no_db
    )
    downloaded = downloader.search_and_download(args.query, args.num)
    
    print(f"\nTotal downloaded: {len(downloaded)} images")


if __name__ == "__main__":
    main()
