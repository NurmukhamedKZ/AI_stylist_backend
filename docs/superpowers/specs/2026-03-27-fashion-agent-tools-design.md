# Fashion Agent Tools — Design Spec
**Date:** 2026-03-27

## Overview

A single LangChain agent with tools split across two domain files. The agent takes a user's style request, searches Pinterest for relevant clothing items, evaluates their compatibility, generates an outfit image via Gemini, and returns a structured outfit card.

## Architecture

```
User request
    │
    ▼
Agent (LangChain, single agent)
    ├── catalog_tools.py
    │       └── search_fashion_items
    └── stylist_tools.py
            ├── evaluate_outfit
            ├── generate_outfit_image
            └── build_outfit_card
```

## Tools

### `catalog_tools.py`

#### `search_fashion_items(query: str, num_images: int = 10) -> list[str]`
- Wraps `PinterestSearcher.search()` from `scripts/pinterest_search.py`
- Returns list of Pinterest image URLs
- Agent calls this multiple times for different clothing categories (top, bottom, shoes, etc.)

---

### `stylist_tools.py`

#### `evaluate_outfit(image_urls: list[str]) -> str`
- Passes image URLs to GPT-4o Vision (`gpt-4o`)
- Prompt asks: do these items work together as an outfit? Why/why not?
- Returns natural language assessment

#### `generate_outfit_image(outfit_description: str) -> str`
- Calls `gemini-3.1-flash-image-preview` via `google-genai` SDK
- Input: text description of the outfit (style, colors, pieces)
- Saves generated image to `data/outfits/<uuid>.png`
- Returns file path

#### `build_outfit_card(image_urls: list[str], generated_image_path: str, description: str) -> dict`
- Pure Python, no LLM calls
- Assembles final structured response:
  ```json
  {
    "items": ["url1", "url2", ...],
    "outfit_image": "/outfits/<uuid>.png",
    "description": "...",
  }
  ```

## Data Flow

1. User: *"найди casual образ в тёмных тонах"*
2. Agent → `search_fashion_items("dark casual top men", 5)` → URLs
3. Agent → `search_fashion_items("dark casual trousers men", 5)` → URLs
4. Agent → `evaluate_outfit([top_url, bottom_url, ...])` → compatibility text
5. Agent → `generate_outfit_image("casual dark outfit: navy crew-neck, black slim jeans...")` → path
6. Agent → `build_outfit_card(urls, path, description)` → final response

## Tech Stack

| Component | Library |
|-----------|---------|
| Pinterest search | `playwright` (existing `PinterestSearcher`) |
| Outfit evaluation | `langchain-openai` → `gpt-4o` |
| Image generation | `google-genai` → `gemini-3.1-flash-image-preview` |
| Tool decorator | `langchain.tools.tool` |

## File Structure

```
app/
  tools/
    __init__.py
    catalog_tools.py
    stylist_tools.py
```

## Error Handling

- `search_fashion_items`: returns empty list on Pinterest timeout, agent retries with different query
- `evaluate_outfit`: raises `ValueError` if no image URLs provided
- `generate_outfit_image`: raises on Gemini API error, does not retry

## Out of Scope

- Color extraction (HSL analysis) — GPT-4o Vision handles color assessment implicitly
- Budget filtering — no price data available yet
- Multi-agent architecture — single agent for now, split later if needed
