# Agent Visual Item Selection — Design Spec

**Date:** 2026-03-28

## Problem

The main agent receives only text URLs from `search_fashion_items`. It cannot see the actual clothing items, so it blindly passes all URLs downstream without making any visual selection. The goal is for the agent to visually inspect found items, compose multiple outfit combinations, and pick the best one.

## Solution

Modify `search_fashion_items` to return multimodal content (text + image_url blocks) so the agent's LLM (GPT-4o) can see the clothing images directly in the ToolMessage. Update the system prompt to instruct the agent to use this visual capability to compose and evaluate multiple outfit combinations.

## Architecture

Two files change:

1. **`app/tools/catalog_tools.py`** — `search_fashion_items` return format
2. **`app/services/agent.py`** — system prompt

## Data Flow

```
User prompt
    │
    ▼
search_fashion_items (parallel, per category)
    │ returns: [text(urls json), image_url, image_url, ...]
    │ Agent SEES the images
    ▼
Agent visually selects items → composes 2-3 outfit combinations
    │
    ▼
evaluate_outfit (parallel, one call per combination)
    │ returns: text compatibility assessment
    ▼
Agent picks best combination
    │
    ▼
generate_outfit_image(description, urls_of_selected_items)
    │ returns: path to generated PNG
    ▼
Final outfit card (URLs + image path + styling explanation)
```

## Changes

### `search_fashion_items` return format

Instead of returning a plain `dict`, the tool returns a list of content blocks:

```python
[
    {"type": "text", "text": json.dumps({"status": "success", "query": query, "urls": urls})},
    {"type": "image_url", "image_url": {"url": urls[0]}},
    {"type": "image_url", "image_url": {"url": urls[1]}},
    ...
]
```

- The `text` block preserves machine-readable URL data for the agent to pass downstream.
- The `image_url` blocks allow GPT-4o to visually inspect each item.
- Error and no_results cases return a plain text string (no images to show).

### System prompt updates

The new prompt instructs the agent to:
1. Call `search_fashion_items` for all categories in parallel.
2. **Look at the returned images** and select visually appealing items.
3. Compose **2-3 outfit combinations** from the selected items.
4. Call `evaluate_outfit` in parallel for each combination.
5. Pick the best combination based on evaluation results.
6. Call `generate_outfit_image` with a detailed description and the URLs of the chosen items.
7. Return a final outfit card explaining the choice.

## Constraints

- Pinterest `pinimg.com` URLs must be accessible to OpenAI's vision API. This is the expected behavior and works in practice.
- No new tools are added.
- No changes to `evaluate_outfit` or `generate_outfit_image`.
