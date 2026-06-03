from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import ai

app = FastAPI(title="Smart Recycle AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router, prefix="/ai", tags=["AI"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "smart-recycle-api"}
