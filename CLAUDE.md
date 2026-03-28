# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Always use context7 before writing any code in Langchain/Langgraph

## Commands

This project uses `uv` for dependency management (Python 3.13).

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn main:app --reload

# Run a script
uv run python scripts/pinterest_search.py

# Run Jupyter notebook
uv run jupyter notebook scripts/embedding.ipynb
```

Required environment variables (create `.env`):
```
GEMINI_API_KEY=
QDRANT_URL=
QDRANT_API_KEY=
```

## Architecture

**AI fashion recommendation backend** — FastAPI app that ingests clothing datasets, generates multimodal embeddings, and serves similarity-based outfit recommendations.

### Data Flow

1. `POST /ingest` → reads image + JSON annotations from `data/` → crops bounding boxes (PIL) → generates 3072-dim Gemini Embedding 2 vectors → stores metadata in SQLite (`fashion.db`) + vectors in Qdrant
2. `GET /items/{item_id}/recommend` → fetches item vector from Qdrant → filters by category compatibility + source → re-ranks by quality signals → returns top-N from SQLite

### Storage

- **SQLite** (`fashion.db`): item metadata via SQLAlchemy ORM (`Image`, `ClothingItem` models)
- **Qdrant** (cloud): vector store with `clothing_items` collection, COSINE distance, 3072 dims
- **`data/crops/`**: generated crop images served as static files at `/crops`

### Recommendation Logic (`app/services/recommendation.py`)

Compatibility filtering determines which category groups can be recommended together:
- `top` ↔ `bottom`, `outerwear`
- `bottom` ↔ `top`, `outerwear`
- `outerwear` ↔ all groups
- `dress` ↔ `outerwear` only

Re-ranking applies quality bonus for low occlusion + frontal viewpoint.

### Annotation Format

DeepFashion2-style JSON: `{"item 1": {category_id, category_name, bounding_box, style, scale, occlusion, zoom_in, viewpoint}, "item 2": {...}}`

### Scripts

- `scripts/pinterest_search.py`: Playwright-based Pinterest scraper — `PinterestSearcher.search(query, num_images)` returns image URLs
- `scripts/embedding.ipynb`: exploratory notebook for Gemini embedding experiments
