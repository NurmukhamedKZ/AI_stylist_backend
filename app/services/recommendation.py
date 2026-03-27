import os

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue

from app.config import QDRANT_COLLECTION
from app.db.qdrant import get_qdrant
from app.models.clothing import ClothingItem, CategoryGroup

COMPATIBLE_GROUPS: dict[str, list[str]] = {
    CategoryGroup.top.value:      [CategoryGroup.bottom.value, CategoryGroup.outerwear.value],
    CategoryGroup.bottom.value:   [CategoryGroup.top.value, CategoryGroup.outerwear.value],
    CategoryGroup.outerwear.value:[CategoryGroup.top.value, CategoryGroup.bottom.value, CategoryGroup.dress.value],
    CategoryGroup.dress.value:    [CategoryGroup.outerwear.value],
}

# Re-ranking bonus: prefer clean frontal shop images
def _quality_bonus(payload: dict) -> float:
    bonus = 0.0
    if payload.get("occlusion") == 1:
        bonus += 0.02
    if payload.get("viewpoint") == 2:
        bonus += 0.02
    return bonus


def get_recommendations(
    item_id: str,
    db: Session,
    top_n: int = 10,
    source: str | None = "shop",
) -> dict:
    item: ClothingItem | None = db.get(ClothingItem, item_id)
    if item is None:
        return None

    compatible = COMPATIBLE_GROUPS.get(item.category_group.value, [])
    if not compatible:
        return {"source_item": item_dict(item), "recommendations": []}

    qdrant = get_qdrant()

    # Fetch the query vector from Qdrant
    results = qdrant.retrieve(
        collection_name=QDRANT_COLLECTION,
        ids=[item_id],
        with_vectors=True,
    )
    if not results:
        return {"source_item": item_dict(item), "recommendations": []}

    query_vector = results[0].vector

    # Build filter
    must_conditions = [
        FieldCondition(key="category_group", match=MatchAny(any=compatible))
    ]
    if source and source != "both":
        must_conditions.append(
            FieldCondition(key="source", match=MatchValue(value=source))
        )

    search_results = qdrant.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(must=must_conditions),
        limit=top_n * 2,  # fetch extra for re-ranking
        with_payload=True,
    )

    # Re-rank: score + quality bonus
    ranked = sorted(
        search_results,
        key=lambda r: r.score + _quality_bonus(r.payload),
        reverse=True,
    )[:top_n]

    # Batch-load all recommendation items in one query
    ranked_ids = [hit.id for hit in ranked]
    items_by_id = {
        row.id: row
        for row in db.execute(
            select(ClothingItem)
            .where(ClothingItem.id.in_(ranked_ids))
            .options(joinedload(ClothingItem.image))
        ).scalars()
    }

    recommendations = []
    for hit in ranked:
        rec_item = items_by_id.get(str(hit.id))
        if rec_item is None:
            continue
        rec_dict = item_dict(rec_item)
        rec_dict["score"] = round(hit.score + _quality_bonus(hit.payload), 4)
        recommendations.append(rec_dict)

    return {
        "source_item": item_dict(item),
        "recommendations": recommendations,
    }


def item_dict(item: ClothingItem) -> dict:
    return {
        "id": item.id,
        "image_id": item.image_id,
        "category_id": item.category_id,
        "category_name": item.category_name,
        "category_group": item.category_group.value,
        "style": item.style,
        "bounding_box": item.bounding_box,
        "scale": item.scale,
        "occlusion": item.occlusion,
        "viewpoint": item.viewpoint,
        "crop_url": f"/crops/{os.path.basename(item.crop_path)}" if item.crop_path else None,
        "source": item.image.source.value if item.image else None,
    }
