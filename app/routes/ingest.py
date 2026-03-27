import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import DATA_DIR
from app.db.session import get_db
from app.services.ingestion import ingest_dataset

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    images_dir: str
    annotations_dir: str


def _safe_path(user_path: str) -> str:
    """Resolve path and ensure it stays within DATA_DIR."""
    resolved = os.path.realpath(user_path)
    if not resolved.startswith(DATA_DIR + os.sep) and resolved != DATA_DIR:
        raise HTTPException(
            status_code=400,
            detail="Path must be inside the data directory",
        )
    return resolved


@router.post("")
def ingest(body: IngestRequest, db: Session = Depends(get_db)):
    images_dir = _safe_path(body.images_dir)
    annotations_dir = _safe_path(body.annotations_dir)
    try:
        result = ingest_dataset(images_dir, annotations_dir, db)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Ingestion failed")
        raise HTTPException(status_code=500, detail="Ingestion failed. Check server logs.")
    return result
