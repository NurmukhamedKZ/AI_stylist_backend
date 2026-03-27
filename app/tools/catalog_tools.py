from langchain.tools import tool

from scripts.pinterest_search import PinterestSearcher


@tool
def search_fashion_items(query: str, num_images: int = 10) -> dict:
    """
    Searches Pinterest for fashion items matching the query.

    Use this tool to find clothing items for each category separately.
    Call once per category (e.g. once for tops, once for bottoms, once for shoes).

    Input:
      - query: descriptive search term (e.g. "dark navy slim fit jeans men")
      - num_images: number of results to return (default 10, max 20)

    Returns dict with:
      - urls: list of Pinterest image URLs (empty on error or no results)
      - status: "success" | "timeout" | "no_results"
      - query: the original query (use when retrying with modified terms)
      - error_message: present only when status is "timeout"

    If status is "timeout": retry with a simpler, shorter query.
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
            "status": "timeout",
            "query": query,
            "error_message": f"Search failed: {e}. Retry with a simpler query.",
        }
