from langchain.tools import tool

from app.services.pinterest_search import PinterestSearcher


@tool
def search_fashion_items(query: str, num_images: int = 3) -> dict:
    """
    Searches Pinterest for fashion items matching the query.

    Use this tool to find clothing items for each category separately.
    Call once per category (e.g. once for tops, once for bottoms, once for shoes).

    Input:
      - query: descriptive search term (e.g. "dark navy slim fit jeans men")
      - num_images: number of results to return (default 3, max 10)

    Returns dict with:
      - urls: list of Pinterest image URLs (empty on error or no results)
      - status: "success" | "error" | "no_results"
      - query: the original query (use when retrying with modified terms)
      - errorCategory: "transient" (present when status is "error")
      - isRetryable: True (present when status is "error")
      - error_message: present when status is "error"

    If status is "error" (errorCategory "transient"): retry with a simpler, shorter query.
    If status is "no_results": retry with broader search terms.
    Do NOT use for: evaluating outfits, generating images, or building cards.
    """
    try:
        searcher = PinterestSearcher(headless=True)
        urls = searcher.search(query, num_images)

        if not urls:
            return {"urls": [], "status": "no_results", "query": query}

        return {"urls": urls, "status": "success", "query": query}

    except Exception as e:
        return {
            "urls": [],
            "status": "error",
            "errorCategory": "transient",
            "isRetryable": True,
            "query": query,
            "error_message": f"Pinterest search failed: {e}. Retry with a shorter query.",
        }
