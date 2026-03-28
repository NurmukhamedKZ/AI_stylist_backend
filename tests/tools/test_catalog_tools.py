import json
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

    if isinstance(result, list):
        data = json.loads(result[0]["text"])
    else:
        data = json.loads(result)
    assert data["status"] == "no_results"


def test_error_returns_text_string():
    with patch("app.tools.catalog_tools.PinterestSearcher") as mock_cls:
        mock_cls.return_value.search.side_effect = RuntimeError("network timeout")
        result = _invoke("white sneakers")

    if isinstance(result, list):
        data = json.loads(result[0]["text"])
    else:
        data = json.loads(result)
    assert data["status"] == "error"
    assert data["isRetryable"] is True
