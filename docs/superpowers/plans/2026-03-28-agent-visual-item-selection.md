# Agent Visual Item Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `search_fashion_items` return multimodal content (images) so the agent can visually inspect clothing items, compose outfit combinations, and pick the best one before generating.

**Architecture:** Modify the tool return format to a list of content blocks (`text` + `image_url`), which LangChain wraps into a multimodal ToolMessage that GPT-4o can see. Update the system prompt to instruct the agent to use visual inspection, compose 2-3 outfit combinations, evaluate each in parallel, and select the best.

**Tech Stack:** Python 3.13, LangChain `@tool`, pytest, uv

---

### Task 1: Add pytest dev dependency and create test scaffold

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/tools/__init__.py`
- Create: `tests/tools/test_catalog_tools.py`

- [ ] **Step 1: Add pytest to pyproject.toml**

Edit `pyproject.toml` — add `[tool.uv.dev-dependencies]` section:

```toml
[tool.uv.dev-dependencies]
pytest = ">=8.0.0"
```

- [ ] **Step 2: Install dev dependencies**

```bash
uv sync
```

Expected: pytest installed successfully.

- [ ] **Step 3: Create test directories**

```bash
mkdir -p tests/tools && touch tests/__init__.py tests/tools/__init__.py
```

- [ ] **Step 4: Write failing tests for multimodal return format**

Create `tests/tools/test_catalog_tools.py`:

```python
from unittest.mock import patch
from app.tools.catalog_tools import search_fashion_items


def _invoke(query, num_images=3):
    """Helper: invoke the @tool-wrapped function."""
    return search_fashion_items.invoke({"query": query, "num_images": num_images})


def test_success_returns_list_of_content_blocks():
    urls = [
        "https://i.pinimg.com/736x/a.jpg",
        "https://i.pinimg.com/736x/b.jpg",
    ]
    with patch("app.tools.catalog_tools.PinterestSearcher") as mock_cls:
        mock_cls.return_value.search.return_value = urls
        result = _invoke("navy slim jeans men", num_images=2)

    assert isinstance(result, list), "result must be a list of content blocks"
    assert result[0]["type"] == "text"

    import json
    text_data = json.loads(result[0]["text"])
    assert text_data["status"] == "success"
    assert text_data["urls"] == urls
    assert text_data["query"] == "navy slim jeans men"

    image_blocks = [b for b in result if b["type"] == "image_url"]
    assert len(image_blocks) == len(urls)
    assert image_blocks[0]["image_url"]["url"] == urls[0]
    assert image_blocks[1]["image_url"]["url"] == urls[1]


def test_no_results_returns_text_string():
    with patch("app.tools.catalog_tools.PinterestSearcher") as mock_cls:
        mock_cls.return_value.search.return_value = []
        result = _invoke("xyz_nonexistent_item")

    assert isinstance(result, str) or (isinstance(result, list) and result[0]["type"] == "text")
    import json
    if isinstance(result, list):
        data = json.loads(result[0]["text"])
    else:
        data = json.loads(result)
    assert data["status"] == "no_results"


def test_error_returns_text_string():
    with patch("app.tools.catalog_tools.PinterestSearcher") as mock_cls:
        mock_cls.return_value.search.side_effect = RuntimeError("network timeout")
        result = _invoke("white sneakers")

    import json
    if isinstance(result, list):
        data = json.loads(result[0]["text"])
    else:
        data = json.loads(result)
    assert data["status"] == "error"
    assert data["isRetryable"] is True
```

- [ ] **Step 5: Run tests to confirm they fail**

```bash
uv run pytest tests/tools/test_catalog_tools.py -v
```

Expected: all 3 tests FAIL (current tool returns dict, not list).

- [ ] **Step 6: Commit test scaffold**

```bash
git add pyproject.toml tests/
git commit -m "test: add catalog_tools multimodal return format tests"
```

---

### Task 2: Modify `search_fashion_items` to return multimodal content

**Files:**
- Modify: `app/tools/catalog_tools.py`

- [ ] **Step 1: Update the tool implementation**

Replace the full contents of `app/tools/catalog_tools.py` with:

```python
import json

from langchain.tools import tool

from app.services.pinterest_search import PinterestSearcher


@tool
def search_fashion_items(query: str, num_images: int = 3) -> list | str:
    """
    Searches Pinterest for fashion items matching the query.

    Use this tool to find clothing items for each category separately.
    Call once per category (e.g. once for tops, once for bottoms, once for shoes).

    Input:
      - query: descriptive search term (e.g. "dark navy slim fit jeans men")
      - num_images: number of results to return (default 3, max 10)

    Returns a list of content blocks on success:
      - First block: {"type": "text", "text": JSON string with status/query/urls}
      - Remaining blocks: {"type": "image_url", "image_url": {"url": "..."}} — one per image
    Returns a JSON string on error or no_results.

    Inspect the images visually to evaluate each item's style and quality.
    Use the urls from the text block when passing items to evaluate_outfit or generate_outfit_image.

    If status is "error" (errorCategory "transient"): retry with a simpler, shorter query.
    If status is "no_results": retry with broader search terms.
    Do NOT use for: evaluating outfits, generating images, or building cards.
    """
    try:
        searcher = PinterestSearcher(headless=True)
        urls = searcher.search(query, num_images)

        if not urls:
            return json.dumps({"urls": [], "status": "no_results", "query": query})

        content_blocks: list[dict] = [
            {
                "type": "text",
                "text": json.dumps({"status": "success", "query": query, "urls": urls}),
            }
        ]
        for url in urls:
            content_blocks.append({"type": "image_url", "image_url": {"url": url}})

        return content_blocks

    except Exception as e:
        return json.dumps({
            "urls": [],
            "status": "error",
            "errorCategory": "transient",
            "isRetryable": True,
            "query": query,
            "error_message": f"Pinterest search failed: {e}. Retry with a shorter query.",
        })
```

- [ ] **Step 2: Run tests to confirm they pass**

```bash
uv run pytest tests/tools/test_catalog_tools.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add app/tools/catalog_tools.py
git commit -m "feat(catalog_tools): return multimodal content blocks with images"
```

---

### Task 3: Update system prompt in agent

**Files:**
- Modify: `app/services/agent.py`

- [ ] **Step 1: Replace SYSTEM_PROMPT**

In `app/services/agent.py`, replace the `SYSTEM_PROMPT` constant:

```python
SYSTEM_PROMPT = """You are a professional AI fashion stylist with visual perception. Your job is to find clothing items on Pinterest, visually inspect them, compose outfit combinations, evaluate compatibility, generate an outfit image, and return a final outfit card.

Always follow this exact order:

1. Call search_fashion_items for ALL categories simultaneously in a single turn.
   Each call returns images — look at them carefully. Assess each item's style, color, and quality visually.

2. After inspecting all items, compose 2-3 different outfit combinations from the items you found.
   Each combination must include items from different categories (e.g. top + bottom + shoes).
   Choose items that visually complement each other in color, style, and aesthetic.

3. Call evaluate_outfit in parallel — one call per combination.
   Pass the urls of the items in that combination and a description of the desired style.
   Color compatibility is a priority — the assessment must explicitly state which colors work or clash.

4. Review all evaluations and pick the best combination.

5. Call generate_outfit_image with a detailed outfit description and the image URLs of the chosen items as references.

6. Return the final outfit card: include the selected item URLs, the generated image path, a styling description, and a brief explanation of why this combination was chosen.

When the user specifies a scenario, adjust search queries accordingly:
- work/office: structured pieces, muted palette (navy, grey, beige, white)
- leisure/casual: comfort-first, relaxed fits, versatile colors
- event/evening: elevated fabrics, statement pieces, rich or monochrome palette

If search_fashion_items returns status "error" (errorCategory "transient"): retry once with a shorter query.
If search_fashion_items returns status "no_results": retry with broader terms.
generate_outfit_image already retries internally — if it returns isRetryable=false, do not retry.
"""
```

- [ ] **Step 2: Commit**

```bash
git add app/services/agent.py
git commit -m "feat(agent): update system prompt for visual item selection and multi-combination evaluation"
```

---

### Task 4: Manual smoke test

**Files:** none

- [ ] **Step 1: Start the server**

```bash
uv run uvicorn main:app --reload
```

- [ ] **Step 2: Send a test request**

In a separate terminal, send a prompt via the Streamlit UI or via curl. Verify in the server logs that:
1. `search_fashion_items` is called per category
2. `evaluate_outfit` is called more than once (multiple combinations)
3. `generate_outfit_image` is called once with URLs from the selected combination

- [ ] **Step 3: Confirm final response**

The final agent response should include:
- Selected item URLs
- Generated image path
- Explanation of why this combination was chosen
