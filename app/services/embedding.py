from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY

EMBEDDING_MODEL = "gemini-embedding-2-preview"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def embed_item(crop_path: str, category_name: str) -> list[float]:
    """Generate a 3072-dim embedding from a cropped clothing image + category name."""
    client = _get_client()

    with open(crop_path, "rb") as f:
        image_bytes = f.read()

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
    text_part = types.Part.from_text(text=category_name)

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[image_part, text_part],
    )
    if not response.embeddings or len(response.embeddings[0].values) != 3072:
        raise ValueError(
            f"Unexpected embedding response: got {len(response.embeddings)} embeddings"
            + (f" with dim {len(response.embeddings[0].values)}" if response.embeddings else "")
        )
    return response.embeddings[0].values
