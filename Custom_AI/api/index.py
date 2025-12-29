from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.files_api import router as files_router
from api.chat_api import router as chat_router

app = FastAPI(
    title="Custom AI API",
    description="API for Custom AI - file browsing and chat over documents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router, tags=["files"])
app.include_router(chat_router, tags=["chat"])
