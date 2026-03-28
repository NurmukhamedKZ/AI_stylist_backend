import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel, field_validator
from sse_starlette.sse import EventSourceResponse

from app.services.agent import run_agent_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


class StyleRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be empty")
        return v.strip()


async def _sse_generator(prompt: str):
    try:
        async for event_type, data in run_agent_stream(prompt):
            if event_type == "token":
                yield {"event": "token", "data": json.dumps({"chunk": data})}
            elif event_type == "tool_start":
                yield {"event": "tool_start", "data": json.dumps({"name": data})}
            elif event_type == "tool_end":
                yield {"event": "tool_end", "data": json.dumps(data)}
            elif event_type == "done":
                yield {"event": "done", "data": json.dumps({"result": data})}
    except Exception as exc:
        logger.exception("Agent stream error")
        yield {"event": "error", "data": json.dumps({"detail": str(exc)})}


@router.post("/style")
async def style(body: StyleRequest):
    return EventSourceResponse(_sse_generator(body.prompt))
