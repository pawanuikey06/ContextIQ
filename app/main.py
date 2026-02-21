from fastapi import FastAPI
from app.api.media import router as media_router

app = FastAPI(title="Meeting Intelligence System")

app.include_router(media_router)