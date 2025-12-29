import os
import env_loader
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import List
from openai import AzureOpenAI

from services.graph_service import stream_file_from_onedrive
from services.file_parser import parse_file_from_bytes

router = APIRouter(prefix="/chat")

def get_openai_client():
    key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not key or not endpoint or not deployment:
        raise HTTPException(
            status_code=500,
            detail="Azure OpenAI environment variables are not configured"
        )

    return AzureOpenAI(
        api_key=key,
        api_version="2024-02-15-preview",
        azure_endpoint=endpoint
    )



class ChatRequest(BaseModel):
    question: str
    selected_files: List[dict]
    # Each dict must contain:
    # { file_id: str, drive_id: str, file_name: str }


@router.post("/query")
def query_selected_files(
    req: ChatRequest,
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing access token")

    token = authorization.replace("Bearer ", "")

    if not req.selected_files:
        raise HTTPException(status_code=400, detail="No files selected")

    full_context = ""

    print(" TOTAL FILES RECEIVED:", len(req.selected_files))

    for file in req.selected_files:

        if not file.get("file_id") or not file.get("drive_id") or not file.get("file_name"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file payload: {file}"
            )

        print("\n Fetching file:")
        print("file_id:", file["file_id"])
        print("drive_id:", file["drive_id"])
        print("file_name:", file["file_name"])

        file_bytes = stream_file_from_onedrive(
            file_id=file["file_id"],
            drive_id=file["drive_id"],
            token=token
        )

        print(" FILE BYTES SIZE:", len(file_bytes))

        extracted_text = parse_file_from_bytes(
            file_bytes,
            file["file_name"]
        )

        print(" EXTRACTED TEXT LENGTH:", len(extracted_text))
        print(" EXTRACTED TEXT PREVIEW (FIRST 500 CHARS):")
        print(extracted_text[:500])

        #  APPEND ONLY ONCE (FIXED)
        full_context += f"\n\n--- {file['file_name']} ---\n{extracted_text}"

    #  FINAL CONTEXT SIZE CHECK (CRITICAL DEBUG)
    print("\n FINAL FULL CONTEXT LENGTH SENT TO LLM:", len(full_context))

    #  LLM CALL (WITH SAFE TOKEN LIMIT)
    client = get_openai_client()

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[...],
        temperature=0,
        max_tokens=1500
    )


    return {
        "answer": response.choices[0].message.content
    }
