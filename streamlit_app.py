import json
import os
from pathlib import Path

import httpx
import streamlit as st
from httpx_sse import connect_sse

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

TOOL_ICONS = {
    "search_fashion_items": "🔍",
    "evaluate_outfit": "🎨",
    "generate_outfit_image": "🖼",
}

st.set_page_config(page_title="AI Fashion Stylist", page_icon="👗", layout="centered")
st.title("👗 AI Fashion Stylist")

with st.sidebar:
    base_url = st.text_input("Backend URL", value=BACKEND_URL)

prompt = st.text_area("Опишите желаемый образ", placeholder="smart casual office look for men", height=100)
run = st.button("Создать образ", type="primary", use_container_width=True)

if run and prompt.strip():
    st.divider()

    # Progress section
    st.subheader("Прогресс")
    progress_container = st.container()
    tool_placeholders: dict[str, object] = {}

    # Response section
    st.subheader("Ответ стилиста")
    response_placeholder = st.empty()

    # Image section
    image_placeholder = st.empty()

    response_text = ""
    outfit_image_path: str | None = None

    try:
        with httpx.Client(timeout=None) as client:
            with connect_sse(
                client,
                "POST",
                f"{base_url}/agent/style",
                json={"prompt": prompt},
            ) as event_source:
                for sse in event_source.iter_sse():
                    data = json.loads(sse.data)

                    if sse.event == "tool_start":
                        name = data["name"]
                        icon = TOOL_ICONS.get(name, "🔧")
                        placeholder = progress_container.empty()
                        placeholder.markdown(f"{icon} **{name}** ⏳")
                        tool_placeholders[name] = placeholder

                    elif sse.event == "tool_end":
                        name = data["name"]
                        icon = TOOL_ICONS.get(name, "🔧")
                        if name in tool_placeholders:
                            tool_placeholders[name].markdown(f"{icon} **{name}** ✓")

                        # Extract generated image path
                        output = data.get("output", {})
                        if name == "generate_outfit_image" and isinstance(output, dict):
                            if output.get("status") == "success":
                                outfit_image_path = output.get("path")

                    elif sse.event == "token":
                        response_text += data["chunk"]
                        response_placeholder.markdown(response_text)

                    elif sse.event == "done":
                        if data.get("result"):
                            response_text = data["result"]
                            response_placeholder.markdown(response_text)

                        if outfit_image_path and Path(outfit_image_path).exists():
                            st.divider()
                            st.subheader("Сгенерированный образ")
                            image_placeholder.image(outfit_image_path, use_container_width=True)

                    elif sse.event == "error":
                        st.error(f"Ошибка: {data.get('detail', 'Неизвестная ошибка')}")
                        break

    except httpx.ConnectError:
        st.error(f"Не удалось подключиться к серверу: {base_url}. Убедитесь, что FastAPI запущен.")
    except Exception as e:
        st.error(f"Ошибка: {e}")
