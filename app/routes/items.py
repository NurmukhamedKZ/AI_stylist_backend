from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.clothing import ClothingItem
from app.services.recommendation import get_recommendations, item_dict

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{item_id}")
def get_item(item_id: str, db: Session = Depends(get_db)):
    item: ClothingItem | None = db.get(ClothingItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_dict(item)


@router.get("/{item_id}/recommend")
def recommend(
    item_id: str,
    top_n: int = Query(default=10, ge=1, le=50),
    source: str = Query(default="shop", pattern="^(shop|user|both)$"),
    db: Session = Depends(get_db),
):
    result = get_recommendations(item_id, db, top_n=top_n, source=source)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return result
