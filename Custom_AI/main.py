from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.files_api import router as files_router
from api.chat_api import router as chat_router
# LOADS OPENAI & PINECONE KEYS

app = FastAPI()

#  CORS CONFIGURATION (THIS FIXES YOUR ERROR)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "https://customai-ergxe9bahwbjh2a8.centralindia-01.azurewebsites.net"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


#  ROUTERS
app.include_router(files_router)
app.include_router(chat_router)
