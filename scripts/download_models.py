#!/usr/bin/env python3
"""AI Voice Cover - One-click model downloader.

Downloads all required pretrained models and optionally voice models.

Usage:
    python scripts/download_models.py              # Download base models only
    python scripts/download_models.py --all         # Download base + popular voice models
    python scripts/download_models.py --voice <id>  # Download a specific voice model
"""
import argparse
import os
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
VOICES_DIR = BASE_DIR / "voices"
ASSETS_DIR = BASE_DIR / "assets"
PRETRAINED_DIR = ASSETS_DIR / "pretrained"
PRETRAINED_V2_DIR = ASSETS_DIR / "pretrained_v2"

# ── HuggingFace base models ─────────────────────────────────────────────────
HF_REPO = "lj1995/VoiceConversionWebUI"
HF_BASE = f"https://huggingface.co/{HF_REPO}/resolve/main"

BASE_MODELS = {
    # Feature extraction
    f"{HF_BASE}/assets/hubert/hubert_base.pt":
        ASSETS_DIR / "hubert" / "hubert_base.pt",

    # F0 pitch extraction (RMVPE - best quality)
    f"{HF_BASE}/assets/rmvpe.pt":
        ASSETS_DIR / "rmvpe.pt",

    # RVC v1 pretrained (encoder + decoder)
    f"{HF_BASE}/assets/pretrained_v1/pretrained/f0D32k.pth":
        PRETRAINED_DIR / "f0D32k.pth",
    f"{HF_BASE}/assets/pretrained_v1/pretrained/f0G32k.pth":
        PRETRAINED_DIR / "f0G32k.pth",

    # RVC v2 pretrained (recommended)
    f"{HF_BASE}/assets/pretrained_v2/pretrained_v2/f0D40k.pth":
        PRETRAINED_V2_DIR / "f0D40k.pth",
    f"{HF_BASE}/assets/pretrained_v2/pretrained_v2/f0G40k.pth":
        PRETRAINED_V2_DIR / "f0G40k.pth",

    # Optional: Crepe F0 extraction model
    f"{HF_BASE}/assets/pretrained_v2/pretrained_v2/f0D48k.pth":
        PRETRAINED_V2_DIR / "f0D48k.pth",
    f"{HF_BASE}/assets/pretrained_v2/pretrained_v2/f0G48k.pth":
        PRETRAINED_V2_DIR / "f0G48k.pth",
}

# ── Popular voice models (weights.gg / HuggingFace) ─────────────────────────
# Format: { "display_name": { "url": "...", "files": { "remote_name": "local_name" } } }
VOICE_MODELS = {
    # Example voice models - add more as needed
    "example-en-female": {
        "desc": "English female singing voice (demo)",
        "files": {},  # User downloads from weights.gg / voice-models.com
    },
}


def download_file(url: str, dest: Path, desc: str = "") -> bool:
    """Download a file with progress bar."""
    import urllib.request
    import shutil

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"  ✓ 已存在: {dest.name} ({size_mb:.1f} MB)")
        return True

    label = desc or dest.name
    print(f"  ⬇ 下载中: {label} ...")

    try:
        # Use urllib with progress
        req = urllib.request.Request(url, headers={"User-Agent": "ai-voice-cover/0.1"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 1024 * 1024  # 1MB

            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total * 100
                        mb = downloaded / 1024 / 1024
                        total_mb = total / 1024 / 1024
                        print(f"\r  ⬇ {label}: {mb:.1f}/{total_mb:.1f} MB ({pct:.0f}%)", end="", flush=True)
                    else:
                        mb = downloaded / 1024 / 1024
                        print(f"\r  ⬇ {label}: {mb:.1f} MB", end="", flush=True)

            print()  # newline after progress
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"  ✓ 完成: {dest.name} ({size_mb:.1f} MB)")
            return True

    except Exception as e:
        print(f"  ✗ 失败: {dest.name} — {e}")
        if dest.exists():
            dest.unlink()
        return False


def download_base_models():
    """Download all required base/pretrained models."""
    print("=" * 60)
    print("📦 下载基础模型 (HuBERT + RMVPE + RVC 预训练)")
    print("=" * 60)

    success = 0
    total = len(BASE_MODELS)

    for url, dest in BASE_MODELS.items():
        if download_file(url, dest):
            success += 1

    print(f"\n基础模型: {success}/{total} 成功")
    return success == total


def download_hf_voice(repo_id: str, voice_name: str = ""):
    """Download a voice model from HuggingFace repo."""
    if not voice_name:
        voice_name = repo_id.split("/")[-1]

    voice_dir = VOICES_DIR / voice_name
    voice_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎤 下载音色模型: {repo_id} → voices/{voice_name}/")

    # Try to list files in the HF repo
    api_url = f"https://huggingface.co/api/models/{repo_id}"
    try:
        import json
        import urllib.request
        req = urllib.request.Request(api_url, headers={"User-Agent": "ai-voice-cover/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        siblings = data.get("siblings", [])
        model_files = [
            s["rfilename"] for s in siblings
            if s["rfilename"].endswith((".pth", ".index", ".wav", ".json", ".yaml"))
        ]

        if not model_files:
            print(f"  ⚠ 仓库中没有找到 .pth/.index 文件")
            return False

        print(f"  找到 {len(model_files)} 个模型文件")
        for fname in model_files:
            url = f"https://huggingface.co/{repo_id}/resolve/main/{fname}"
            dest = voice_dir / Path(fname).name
            download_file(url, dest, desc=fname)

        print(f"  ✓ 音色模型已保存到: voices/{voice_name}/")
        return True

    except Exception as e:
        print(f"  ✗ 获取仓库信息失败: {e}")
        return False


def show_voice_model_guide():
    """Print guide on where to find voice models."""
    print()
    print("=" * 60)
    print("🎤 人声模型下载指南")
    print("=" * 60)
    print("""
1. weights.gg     — 最大的 RVC 模型分享站
   https://weights.gg

2. voice-models.com — 27,900+ 模型合集
   https://voice-models.com

3. HuggingFace    — 搜 "RVC" 关键词
   https://huggingface.co/models?search=rvc

4. B站/QQ群       — 中文歌手模型主要在这里

下载后把模型文件夹放到 voices/ 目录:
  voices/
    ├── 歌手名A/
    │   ├── model.pth    ← 必须有
    │   └── model.index  ← 可选，提升质量
    └── 歌手名B/
        ├── xxx.pth
        └── xxx.index
""")


def main():
    parser = argparse.ArgumentParser(description="AI Voice Cover - 模型下载器")
    parser.add_argument("--all", action="store_true", help="下载基础模型 + 显示音色指南")
    parser.add_argument("--voice", type=str, help="从 HuggingFace 下载指定音色模型 (repo_id)")
    parser.add_argument("--voice-name", type=str, default="", help="音色模型本地名称")
    parser.add_argument("--base-only", action="store_true", help="只下载基础模型")
    args = parser.parse_args()

    print()
    print("  🎵 AI Voice Cover - 模型下载器")
    print("  " + "─" * 40)
    print(f"  项目目录: {BASE_DIR}")
    print()

    # Always download base models
    download_base_models()

    # Download specific voice model from HF
    if args.voice:
        download_hf_voice(args.voice, args.voice_name or "")

    # Show guide
    if args.all or not args.voice:
        show_voice_model_guide()

    print("✅ 完成!")
    print()


if __name__ == "__main__":
    main()
