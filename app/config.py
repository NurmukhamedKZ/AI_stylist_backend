from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
QDRANT_URL: str = os.environ["QDRANT_URL"]        # e.g. https://xyz.qdrant.tech
QDRANT_API_KEY: str = os.environ["QDRANT_API_KEY"]  # Qdrant Cloud API key
QDRANT_COLLECTION: str = "clothing_items"
DATA_DIR: str = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "data"))
CROPS_DIR: str = os.path.join(DATA_DIR, "crops")
OUTFITS_DIR: str = os.path.join(DATA_DIR, "outfits")
