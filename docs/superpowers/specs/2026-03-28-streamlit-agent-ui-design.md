# Streamlit Agent UI — Design Spec

**Date:** 2026-03-28
**Status:** Approved

## Overview

A single-page Streamlit app (`streamlit_app.py`) that communicates with the FastAPI backend's `/agent/style` SSE endpoint. Displays real-time tool progress and streams the final stylist response with generated outfit image.

## Architecture

- **File:** `streamlit_app.py` at the project root
- **New dependencies:** `httpx`, `httpx-sse` (added to `pyproject.toml`)
- **No backend changes** — pure HTTP client

Core function:

```python
def stream_agent(prompt: str, base_url: str) -> Generator[tuple[str, dict], None, None]:
    with httpx.stream("POST", f"{base_url}/agent/style", json={"prompt": prompt}, timeout=None) as r:
        for sse in parse_sse(r.iter_lines()):
            yield sse.event, json.loads(sse.data)
```

## UI Layout

```
┌─────────────────────────────────────────┐
│  👗 AI Fashion Stylist                  │
│                                         │
│  [Опишите желаемый образ...        ]    │
│  [        Создать образ            ]    │
│                                         │
│  ── Прогресс ──────────────────────     │
│  🔍 search_fashion_items  ✓             │
│  🎨 evaluate_outfit       ✓             │
│  🖼 generate_outfit_image  ⏳           │
│                                         │
│  ── Ответ стилиста ─────────────────    │
│  [текст стримится сюда...]              │
│                                         │
│  ── Сгенерированный образ ──────────    │
│  [изображение]                          │
└─────────────────────────────────────────┘
```

## Event Handling

| SSE Event    | Action |
|---|---|
| `tool_start` | Append tool row with ⏳ to progress block |
| `tool_end`   | Update matching tool row to ✓ |
| `token`      | Append chunk to response text placeholder |
| `done`       | Finalize response text |
| `error`      | Show `st.error()` with detail message |

Image display: parse `tool_end` for `generate_outfit_image` → extract `output.path` → `st.image(path)`.

## Tool Icon Mapping

| Tool name | Icon |
|---|---|
| `search_fashion_items` | 🔍 |
| `evaluate_outfit` | 🎨 |
| `generate_outfit_image` | 🖼 |
| (default) | 🔧 |

## Configuration

`BASE_URL` defaults to `http://localhost:8000`, overridable via `BACKEND_URL` env var or a sidebar text input in the UI.
