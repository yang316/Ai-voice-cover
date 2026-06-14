"""HuggingFace Hub integration for downloading voice models."""
import json
import logging
from pathlib import Path

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

HF_API = "https://huggingface.co/api"
HF_MODELS = "https://huggingface.co/models"

# Known RVC/SoVITS model repos
KNOWN_RVC_REPOS = [
    "RVC-Project/Retrieval-based-Voice-Conversion-WebUI",
    "liaorwork/rvc-models",
]


async def search_voice_models(
    query: str = "",
    limit: int = 20,
) -> list[dict]:
    """Search HuggingFace for voice conversion models."""
    async with httpx.AsyncClient(timeout=30) as client:
        params = {
            "search": query or "rvc voice conversion",
            "sort": "downloads",
            "direction": "-1",
            "limit": limit,
            "filter": "rvc",
        }

        resp = await client.get(
            f"{HF_API}/models",
            params=params,
            headers={"Authorization": f"Bearer {settings.hf_token}"} if settings.hf_token else {},
        )

        if resp.status_code != 200:
            logger.error(f"HF search failed: {resp.status_code}")
            return []

        models = resp.json()
        results = []
        for m in models:
            results.append({
                "id": m.get("id", ""),
                "author": m.get("author", ""),
                "downloads": m.get("downloads", 0),
                "likes": m.get("likes", 0),
                "tags": m.get("tags", []),
                "last_modified": m.get("lastModified", ""),
            })

        return results


async def download_model(
    repo_id: str,
    filename: str,
    voice_id: str,
    revision: str = "main",
) -> Path:
    """
    Download a model file from HuggingFace Hub.

    Args:
        repo_id: HuggingFace repo ID (e.g. "user/repo")
        filename: File to download (e.g. "model.pth")
        voice_id: Local voice ID to save as
        revision: Branch/tag/commit

    Returns: path to downloaded file
    """
    voice_dir = settings.voices_dir / voice_id
    voice_dir.mkdir(parents=True, exist_ok=True)

    output_path = voice_dir / filename

    if output_path.exists():
        logger.info(f"Model already exists: {output_path}")
        return output_path

    url = f"https://huggingface.co/{repo_id}/resolve/{revision}/{filename}"
    headers = {}
    if settings.hf_token:
        headers["Authorization"] = f"Bearer {settings.hf_token}"

    logger.info(f"Downloading {repo_id}/{filename} -> {output_path}")

    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream("GET", url, headers=headers, follow_redirects=True) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"Download failed: {resp.status_code} {resp.text[:200]}")

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(output_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

    # Save metadata
    meta = {
        "id": voice_id,
        "name": voice_id.replace("_", " ").title(),
        "source": f"huggingface:{repo_id}",
        "filename": filename,
        "repo_id": repo_id,
    }
    meta_path = voice_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    logger.info(f"Downloaded: {output_path} ({downloaded / 1024 / 1024:.1f} MB)")
    return output_path


async def list_repo_files(repo_id: str, revision: str = "main") -> list[str]:
    """List files in a HuggingFace repo."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{HF_API}/models/{repo_id}/tree/{revision}",
            headers={"Authorization": f"Bearer {settings.hf_token}"} if settings.hf_token else {},
        )

        if resp.status_code != 200:
            return []

        files = resp.json()
        return [f["path"] for f in files if f.get("type") == "file"]
