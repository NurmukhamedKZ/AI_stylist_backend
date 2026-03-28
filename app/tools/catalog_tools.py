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
