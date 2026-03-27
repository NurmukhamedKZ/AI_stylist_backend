import os
import uuid
from pathlib import Path

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from google import genai

from app.config import GEMINI_API_KEY

OUTFITS_DIR = Path(__file__).parent.parent.parent / "data" / "outfits"
OUTFITS_DIR.mkdir(parents=True, exist_ok=True)

_openai_client: ChatOpenAI | None = None
_gemini_client: genai.Client | None = None


def _get_openai() -> ChatOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = ChatOpenAI(model="gpt-4o")
    return _openai_client


def _get_gemini() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


@tool
def evaluate_outfit(image_urls: list[str]) -> str:
    """
    Evaluates visual compatibility of clothing items as a complete outfit.

    Use ONLY after search_fashion_items has returned URLs for ALL required
    categories (minimum: top + bottom, ideally top + bottom + shoes).
    Do NOT call with fewer than 2 URLs.

    Input:
      - image_urls: list of Pinterest image URLs (2–6 items)

    Output: natural language compatibility assessment covering
    color harmony, style consistency, and overall aesthetic.

    Do NOT use for: searching items, generating images, or building cards.
    Call this BEFORE generate_outfit_image.
    """
    if len(image_urls) < 2:
        raise ValueError(
            f"evaluate_outfit requires at least 2 image URLs, got {len(image_urls)}. "
            "Call search_fashion_items for more categories first."
        )

    llm = _get_openai()

    content = [
        {
            "type": "text",
            "text": (
                "You are a professional fashion stylist. Evaluate whether these clothing items "
                "work together as a complete outfit. Assess: color harmony, style consistency, "
                "and overall aesthetic. Be specific about what works and what doesn't."
            ),
        }
    ]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})

    response = llm.invoke([{"role": "user", "content": content}])
    return response.content


@tool
def generate_outfit_image(outfit_description: str) -> dict:
    """
    Generates a fashion outfit image using Gemini image generation.

    Call this AFTER evaluate_outfit confirms the items are compatible.

    Input:
      - outfit_description: detailed text description of the outfit
        (style, colors, specific pieces, e.g. "casual dark outfit: navy crew-neck
        sweater, black slim jeans, white minimal sneakers")

    Returns dict with:
      - status: "success" | "error"
      - path: absolute file path to saved PNG (present on success)
      - attempted_description: the input description (always present, useful for retry)
      - error_type: exception class name (present on error)
      - error_message: description of the error (present on error)
      - is_retryable: True if a retry may succeed (present on error)

    Do NOT use for: searching items or evaluating outfits.
    Call BEFORE build_outfit_card.
    """
    try:
        client = _get_gemini()

        prompt = (
            f"Create a high-quality fashion lookbook photo showing this outfit: {outfit_description}. "
            "Studio lighting, clean white background, professional fashion photography style."
        )

        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[prompt],
        )

        image_path: str | None = None
        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                filename = f"{uuid.uuid4()}.png"
                image_path = str(OUTFITS_DIR / filename)
                image.save(image_path)
                break

        if image_path is None:
            return {
                "status": "error",
                "error_type": "NoImageGenerated",
                "error_message": "Gemini returned no image data.",
                "is_retryable": True,
                "attempted_description": outfit_description,
            }

        return {
            "status": "success",
            "path": image_path,
            "attempted_description": outfit_description,
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "is_retryable": isinstance(e, (TimeoutError, ConnectionError)),
            "attempted_description": outfit_description,
        }


@tool
def build_outfit_card(
    image_urls: list[str],
    generated_image_path: str,
    description: str,
) -> dict:
    """
    Assembles the final outfit card returned to the user.

    Call this LAST — only after both evaluate_outfit and generate_outfit_image
    have completed successfully.

    Input:
      - image_urls: list of Pinterest item URLs from search_fashion_items
      - generated_image_path: absolute file path returned by generate_outfit_image
        (must not be empty — call generate_outfit_image first)
      - description: natural language outfit description for the user

    Returns structured outfit response:
      {
        "items": [...],           # Pinterest source URLs
        "outfit_image": "...",    # public path to generated image
        "description": "..."      # styling summary
      }

    Do NOT use for: searching, evaluating, or generating images.
    """
    if not generated_image_path:
        raise ValueError(
            "build_outfit_card requires a generated_image_path. "
            "Call generate_outfit_image first and pass its returned 'path' value."
        )
    if not image_urls:
        raise ValueError(
            "build_outfit_card requires at least one item URL. "
            "Call search_fashion_items first."
        )

    outfit_filename = os.path.basename(generated_image_path)

    return {
        "items": image_urls,
        "outfit_image": f"/outfits/{outfit_filename}",
        "description": description,
    }
