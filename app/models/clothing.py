import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class Source(str, enum.Enum):
    shop = "shop"
    user = "user"


class CategoryGroup(str, enum.Enum):
    top = "top"
    bottom = "bottom"
    outerwear = "outerwear"
    dress = "dress"


# category_id → category_group mapping (DeepFashion2)
CATEGORY_GROUP_MAP: dict[int, CategoryGroup] = {
    1: CategoryGroup.top,        # short sleeve top
    2: CategoryGroup.top,        # long sleeve top
    3: CategoryGroup.outerwear,  # short sleeve outwear
    4: CategoryGroup.outerwear,  # long sleeve outwear
    5: CategoryGroup.top,        # vest
    6: CategoryGroup.top,        # sling
    7: CategoryGroup.bottom,     # shorts
    8: CategoryGroup.bottom,     # trousers
    9: CategoryGroup.bottom,     # skirt
    10: CategoryGroup.dress,     # short sleeve dress
    11: CategoryGroup.dress,     # long sleeve dress
    12: CategoryGroup.dress,     # vest dress
    13: CategoryGroup.dress,     # sling dress
}


class Image(Base):
    __tablename__ = "images"

    image_id = Column(String, primary_key=True)  # e.g. "000001"
    source = Column(SAEnum(Source), nullable=False)
    pair_id = Column(Integer, nullable=False)

    items = relationship("ClothingItem", back_populates="image")


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String, ForeignKey("images.image_id"), nullable=False)
    category_id = Column(Integer, nullable=False)
    category_name = Column(String, nullable=False)
    category_group = Column(SAEnum(CategoryGroup), nullable=False)
    style = Column(Integer, nullable=False, default=0)
    bounding_box = Column(JSON, nullable=False)   # [x1, y1, x2, y2]
    scale = Column(Integer, nullable=True)
    occlusion = Column(Integer, nullable=True)
    zoom_in = Column(Integer, nullable=True)
    viewpoint = Column(Integer, nullable=True)
    crop_path = Column(String, nullable=True)

    image = relationship("Image", back_populates="items")
