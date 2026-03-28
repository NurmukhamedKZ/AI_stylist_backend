# Agent SSE Endpoint Design

**Date:** 2026-03-28
**Feature:** POST /agent/style — streaming AI stylist via Server-Sent Events

## Overview

Expose the existing `AgentExecutor` (LangChain + GPT-4o) over HTTP with SSE streaming so clients receive live tool call events and the final outfit card in real time.

## Endpoint

`POST /agent/style`

- **Request body:** `{"prompt": "smart casual office look"}`
- **Response:** `text/event-stream` (SSE)

## SSE Event Schema

Each event has a named `event` field and a JSON `data` payload:

| event | when | data shape |
|---|---|---|
| `tool_start` | tool invocation begins | `{"name": "search_fashion_items", "input": {...}}` |
| `tool_end` | tool returns | `{"name": "search_fashion_items", "output": {...}}` |
| `done` | agent chain completes | outfit card `{"items": [...], "outfit_image": "...", "description": "..."}` or `{"result": "..."}` if raw text |
| `error` | any exception | `{"detail": "..."}` |

## Architecture

```
client
  │  POST /agent/style {"prompt": "..."}
  ▼
app/routes/agent.py
  │  EventSourceResponse(sse_generator(prompt))
  ▼
sse_generator (async generator)
  │  agent_executor.astream_events({"input": prompt}, version="v2")
  ▼
LangChain events → filtered → typed SSE events → client
```

## Files Changed

- `app/routes/agent.py` — new router with SSE endpoint
- `main.py` — include `agent_router`, mount `/outfits` static dir
- `pyproject.toml` — add `sse-starlette` dependency

## Error Handling

- Empty `prompt` → `422` before stream opens (Pydantic validation)
- Exception inside generator → `event: error` + stream closes cleanly
- Malformed `on_chain_end` output → `event: done` with `{"result": raw_output}`
- Client disconnect → `CancelledError` handled by sse-starlette automatically
