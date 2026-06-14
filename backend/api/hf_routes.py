"""HuggingFace model search and download API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.hf_hub import download_model, list_repo_files, search_voice_models

router = APIRouter()


class HFSearchRequest(BaseModel):
    query: str = ""
    limit: int = 20


class HFDownloadRequest(BaseModel):
    repo_id: str
    filename: str
    voice_id: str
    revision: str = "main"


@router.get("/hf/models")
async def search_models(q: str = "rvc voice", limit: int = 20):
    """Search HuggingFace for voice models."""
    return await search_voice_models(query=q, limit=limit)


@router.get("/hf/models/{repo_id:path}/files")
async def get_repo_files(repo_id: str, revision: str = "main"):
    """List files in a HuggingFace repo."""
    files = await list_repo_files(repo_id, revision)
    return {"repo_id": repo_id, "files": files}


@router.post("/hf/download")
async def download_from_hf(req: HFDownloadRequest):
    """Download a model from HuggingFace to local voices directory."""
    try:
        path = await download_model(
            repo_id=req.repo_id,
            filename=req.filename,
            voice_id=req.voice_id,
            revision=req.revision,
        )
        return {"status": "downloaded", "path": str(path), "voice_id": req.voice_id}
    except Exception as e:
        raise HTTPException(500, str(e))
