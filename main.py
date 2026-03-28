import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import CROPS_DIR, OUTFITS_DIR
from app.db.session import create_tables
from app.db.qdrant import init_collection
from app.routes.agent_routes import router as agent_router
from app.routes.items import router as items_router
from app.routes.ingest import router as ingest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    await asyncio.to_thread(init_collection)
    yield


app = FastAPI(title="AI Fashion Stylist", lifespan=lifespan)
app.include_router(agent_router)
app.include_router(items_router)
app.include_router(ingest_router)
app.mount("/crops", StaticFiles(directory=CROPS_DIR), name="crops")
app.mount("/outfits", StaticFiles(directory=OUTFITS_DIR), name="outfits")
