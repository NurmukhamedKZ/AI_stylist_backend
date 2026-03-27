import json
import os
import uuid
from pathlib import Path

from PIL import Image as PILImage

# Hard cap: reject images larger than 100MP (prevents decompression bomb OOM)
PILImage.MAX_IMAGE_PIXELS = 100_000_000
from sqlalchemy.orm import Session
from qdrant_client.models import PointStruct

from app.config import QDRANT_COLLECTION, CROPS_DIR
from app.db.qdrant import get_qdrant
from app.models.clothing import Image, ClothingItem, CATEGORY_GROUP_MAP, Source
from app.services.embedding import embed_item


def ingest_dataset(images_dir: str, annotations_dir: str, db: Session) -> dict:
    images_dir = Path(images_dir)
    annotations_dir = Path(annotations_dir)
    os.makedirs(CROPS_DIR, exist_ok=True)

    annotation_files = sorted(annotations_dir.glob("*.json"))
    ingested_images = 0
    ingested_items = 0
    skipped = 0

    for ann_file in annotation_files:
        image_id = ann_file.stem  # e.g. "000001"
        image_path = images_dir / f"{image_id}.jpg"

        if not image_path.exists():
            skipped += 1
            continue

        # Skip already-ingested images
        if db.get(Image, image_id):
            continue

        with open(ann_file) as f:
            annotation = json.load(f)

        source_str = annotation.get("source", "shop")
        source = Source.shop if source_str == "shop" else Source.user
        pair_id = annotation.get("pair_id", 0)

        db_image = Image(image_id=image_id, source=source, pair_id=pair_id)
        db.add(db_image)

        pil_img = PILImage.open(image_path).convert("RGB")
        qdrant = get_qdrant()
        points: list[PointStruct] = []

        # Items are stored as "item 1", "item 2", etc. in the annotation
        item_index = 0
        for key, item_data in annotation.items():
            if not key.startswith("item"):
                continue
            if not isinstance(item_data, dict):
                continue

            category_id = item_data.get("category_id")
            category_name = item_data.get("category_name", "")
            bbox = item_data.get("bounding_box")  # [x1, y1, x2, y2]

            if category_id is None or bbox is None:
                continue

            category_group = CATEGORY_GROUP_MAP.get(category_id)
            if category_group is None:
                continue

            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                continue
            x1, y1, x2, y2 = bbox
            # Clamp bounding box to image dimensions
            width, height = pil_img.size
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)

            if x2 <= x1 or y2 <= y1:
                continue

            crop = pil_img.crop((x1, y1, x2, y2))
            crop_filename = f"{image_id}_{item_index}.jpg"
            crop_path = os.path.join(CROPS_DIR, crop_filename)
            crop.save(crop_path, "JPEG")

            item_id = str(uuid.uuid4())
            vector = embed_item(crop_path, category_name)

            db_item = ClothingItem(
                id=item_id,
                image_id=image_id,
                category_id=category_id,
                category_name=category_name,
                category_group=category_group,
                style=item_data.get("style", 0),
                bounding_box=bbox,
                scale=item_data.get("scale"),
                occlusion=item_data.get("occlusion"),
                zoom_in=item_data.get("zoom_in"),
                viewpoint=item_data.get("viewpoint"),
                crop_path=crop_path,
            )
            db.add(db_item)

            points.append(PointStruct(
                id=item_id,
                vector=vector,
                payload={
                    "item_id": item_id,
                    "category_group": category_group.value,
                    "category_id": category_id,
                    "source": source.value,
                    "occlusion": item_data.get("occlusion"),
                    "viewpoint": item_data.get("viewpoint"),
                },
            ))

            item_index += 1
            ingested_items += 1

        if points:
            qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)

        db.commit()
        ingested_images += 1

    return {
        "ingested_images": ingested_images,
        "ingested_items": ingested_items,
        "skipped": skipped,
    }
