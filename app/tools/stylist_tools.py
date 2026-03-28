import uuid
from pathlib import Path

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from google import genai
from langchain.tools import tool, ToolRuntime
from PIL import Image

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
def evaluate_outfit(prompt: str, image_urls: list[str]) -> str:
    """
    Evaluates visual compatibility of clothing items as a complete outfit.

    Use ONLY after search_fashion_items has returned URLs for ALL required
    categories (minimum: top + bottom, ideally top + bottom + shoes).
    Do NOT call with fewer than 2 URLs.

    Input:
      - prompt: the style that user want
      - image_urls: list of Pinterest image URLs (2–6 items)

    Output: text-only compatibility assessment — color harmony (complementary,
    analogous, neutral combinations), style consistency, and overall aesthetic.
    Color compatibility is a priority: explicitly state which colors clash or work.

    INPUT: Only raw Pinterest URLs from search_fashion_items.
    OUTPUT: Text assessment only — no file paths, no structured cards.
    NEVER call this with a generated_image_path as input.
    Do NOT use for: searching items, generating images, or building cards.
    Call this BEFORE generate_outfit_image.
    """
    print("Evaluate_outfit tool:")
    print(len(image_urls))
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
                f"User's preferences: {prompt}"
            ),
        }
    ]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})

    response = llm.invoke([{"role": "user", "content": content}])
    print("Evaluate_outfit Result: ")
    print(response.content)
    return response.content


@tool
def generate_outfit_image(outfit_description: str, image_urls: list[str]) -> dict:
    """
    Generates a fashion outfit image using Gemini image generation.

    Call this AFTER evaluate_outfit confirms the items are compatible.

    Input:
      - outfit_description: detailed text description of the outfit
        (style, colors, specific pieces, e.g. "casual dark outfit: navy crew-neck
        sweater, black slim jeans, white minimal sneakers")
      - image_urls: images urls that can be used as references

    Returns dict with:
      - status: "success" | "error"
      - path: absolute file path to saved PNG (present on success)
      - attempted_description: the input description (always present, useful for retry)
      - errorCategory: "transient" | "validation" (present on error)
      - isRetryable: False — transient errors are already retried internally
      - error_message: human-readable description of the error (present on error)

    Do NOT use for: searching items or evaluating outfits.
    """
    print("Generate_outfit_image tool")
    max_attempts = 2
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            client = _get_gemini()

            prompt = (
                f"Create a high-quality fashion lookbook photo showing this outfit: {outfit_description}. "
                "Studio lighting, clean white background, professional fashion photography style."
            )

            imgs = [Image.open(url) for url in image_urls]

            response = client.models.generate_content(
                model="gemini-3.1-flash-image-preview",
                contents=[prompt] + imgs,
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
                # No image in response — transient, retry once
                last_error = RuntimeError("Gemini returned no image data")
                continue

            return {
                "status": "success",
                "path": image_path,
                "attempted_description": outfit_description,
            }

        except (TimeoutError, ConnectionError) as e:
            last_error = e
            # Transient — retry on next attempt
        except Exception as e:
            # Non-transient (validation, quota, etc.) — fail immediately
            return {
                "status": "error",
                "errorCategory": "validation",
                "isRetryable": False,
                "error_message": f"{type(e).__name__}: {e}",
                "attempted_description": outfit_description,
            }

    return {
        "status": "error",
        "errorCategory": "transient",
        "isRetryable": False,
        "error_message": f"Failed after {max_attempts} attempts: {last_error}",
        "attempted_description": outfit_description,
    }


