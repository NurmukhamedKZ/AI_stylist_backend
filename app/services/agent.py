import json
from typing import AsyncGenerator

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_openai import ChatOpenAI

from app.tools.catalog_tools import search_fashion_items
from app.tools.stylist_tools import evaluate_outfit, generate_outfit_image

load_dotenv()

SYSTEM_PROMPT = """You are a professional AI fashion stylist. Your job is to find clothing items on Pinterest, evaluate their compatibility, generate an outfit image, and return a final outfit card.

Always follow this exact order:
1. Call search_fashion_items for ALL categories simultaneously in a single turn — do not wait for one search to complete before starting another.
2. Call evaluate_outfit with collected URLs. (you can call it parallelly for different outfits) Color compatibility is a priority — the assessment must explicitly state which colors work or clash.
3. Call generate_outfit_image with a detailed outfit description and image urls as references
4. Return the final outfit card in your response: include item URLs, the generated image path, and a styling description.

When the user specifies a scenario, adjust the search queries accordingly:
- work/office: prioritize structured pieces, muted palette (navy, grey, beige, white)
- leisure/casual: comfort-first, relaxed fits, versatile colors
- event/evening: elevated fabrics, statement pieces, rich or monochrome palette

If search_fashion_items returns errorCategory "transient": retry once with a shorter query.
If search_fashion_items returns status "no_results": retry with broader terms.
generate_outfit_image already retries internally — if it returns isRetryable=false, do not retry.
"""

tools = [search_fashion_items, evaluate_outfit, generate_outfit_image]

llm = ChatOpenAI(model="gpt-5.4-mini")

agent = create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)


async def run_agent_stream(prompt: str) -> AsyncGenerator[tuple[str, object], None]:
    """
    Yields (event_type, data) tuples:
      ("token",      str)             — streaming text chunk from final LLM response
      ("tool_start", str)             — tool name being invoked
      ("tool_end",   dict)            — {"name": str, "output": dict | str}
      ("done",       str)             — full final response text
    """
    final_text = ""

    async for stream_mode, chunks in agent.astream(
        {"messages": [{"role": "user", "content": prompt}]},
        stream_mode=["messages", "updates"],
    ):
        if stream_mode == "messages":
            token, _metadata = chunks
            if isinstance(token, AIMessageChunk) and token.content:
                yield ("token", token.content)

        elif stream_mode == "updates":
            for source, update in chunks.items():
                if source == "model":
                    msgs = update.get("messages", [])
                    ai_msg = msgs[-1] if msgs else None
                    if ai_msg is None:
                        continue

                    tool_calls = getattr(ai_msg, "tool_calls", [])
                    for tc in tool_calls:
                        yield ("tool_start", tc["name"])

                    # No tool calls → this is the final LLM response
                    if not tool_calls and getattr(ai_msg, "content", None):
                        final_text = (
                            ai_msg.content
                            if isinstance(ai_msg.content, str)
                            else str(ai_msg.content)
                        )
                        print("Main agent final output:")
                        print(final_text)

                elif source == "tools":
                    for msg in update.get("messages", []):
                        if not isinstance(msg, ToolMessage):
                            continue
                        raw = msg.content
                        try:
                            output = json.loads(raw) if isinstance(raw, str) else raw
                        except (json.JSONDecodeError, TypeError):
                            output = raw
                        yield ("tool_end", {"name": msg.name, "output": output})

    yield ("done", final_text)
