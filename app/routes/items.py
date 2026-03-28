from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage

from app.db.session import get_db
from app.models.clothing import ClothingItem
from app.models.clothing import User
from app.services.recommendation import get_recommendations, item_dict
from app.services.pinterest_search import PinterestSearcher

router = APIRouter(prefix="/items", tags=["items"])


# Custom
@router.get("/")
def home(db: Session = Depends(get_db)):
    searcher = PinterestSearcher()
    return searcher.search("clothes", num_images=40)


@router.get("/clothe")
def get_item_2(img_url: str):
    llm = ChatOpenAI(model="gpt-5.4-nano")

    message = HumanMessage(content=[                                                                                                                                                         
      {"type": "text", "text": "Твоя задача только описать это изображения 5-10 словами\nНе пиши нечего лишнего, не пиши 'хорошо сейчас напишу коротко', от тебя нужно только 5-10 слов"},
      {"type": "image_url", "image_url": {"url": img_url}}
  ])  
    output = llm.invoke([message])

    searcher = PinterestSearcher()
    return searcher.search(output.content, num_images=10)

@router.get("/try_on")
def try_on(img_url: str, user_image: str = None, db: Session = Depends(get_db)):
    if not user_image:
        user_image = db.get(User)

    

    

    

    

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


