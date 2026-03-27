from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION

VECTOR_SIZE = 3072

_client: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _client


def init_collection() -> None:
    client = get_qdrant()
    try:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    except Exception as e:
        # Collection already exists — safe to ignore
        if "already exists" not in str(e).lower():
            raise
