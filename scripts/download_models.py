#!/usr/bin/env python3
"""AI Voice Cover - One-click model downloader.

Usage:
    python scripts/download_models.py              # Download base models
    python scripts/download_models.py --all         # Download base + show guide
    python scripts/download_models.py --voice <id>  # Download a voice model from HF
    python scripts/download_models.py --mirror      # Use hf-mirror.com (国内加速)
"""
import argparse
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VOICES_DIR = BASE_DIR / "voices"

REPO_ID = "lj1995/VoiceConversionWebUI"

# (repo_path, local_relative_path, description)
BASE_FILES = [
    ("hubert_base.pt",            "assets/hubert/hubert_base.pt",  "HuBERT 特征提取模型 (~190MB)"),
    ("rmvpe.pt",                  "assets/rmvpe.pt",               "RMVPE 音高提取模型 (~180MB)"),
    ("pretrained_v2/f0D40k.pth",  "assets/pretrained_v2/f0D40k.pth", "RVC v2 预训练 D (40k)"),
    ("pretrained_v2/f0G40k.pth",  "assets/pretrained_v2/f0G40k.pth", "RVC v2 预训练 G (40k)"),
]


def ensure_hf_hub():
    try:
        import huggingface_hub
        return huggingface_hub
    except ImportError:
        print("📦 安装 huggingface_hub ...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"])
        import huggingface_hub
        return huggingface_hub


def setup_mirror():
    import os
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    print("🪞 使用国内镜像: hf-mirror.com")


def download_file(repo_id, filename, dest, desc=""):
    from huggingface_hub import hf_hub_download

    if dest.exists():
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"  ✓ 已存在: {dest.name} ({size_mb:.1f} MB)")
        return True

    label = desc or filename
    print(f"  ⬇ 下载中: {label}")

    try:
        cached = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=BASE_DIR / ".hf_cache",
            local_dir_use_symlinks=False,
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cached, dest)
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"  ✓ 完成: {dest.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        err = str(e)
        if "404" in err or "Entry Not Found" in err:
            print(f"  ✗ 文件不存在: {filename}")
        elif "401" in err or "403" in err:
            print(f"  ✗ 需要认证，可能需要 huggingface-cli login")
        else:
            print(f"  ✗ 失败: {e}")
        print(f"    💡 如果网络问题，试试 --mirror")
        return False


def download_base():
    print()
    print("=" * 60)
    print("📦 下载基础模型 (HuBERT + RMVPE + RVC v2)")
    print("=" * 60)

    ok = 0
    for repo_path, local_rel, desc in BASE_FILES:
        if download_file(REPO_ID, repo_path, BASE_DIR / local_rel, desc):
            ok += 1

    print(f"\n结果: {ok}/{len(BASE_FILES)} 成功")
    return ok > 0


def download_voice(repo_id, voice_name=""):
    from huggingface_hub import list_repo_tree

    if not voice_name:
        voice_name = repo_id.split("/")[-1]

    voice_dir = VOICES_DIR / voice_name
    voice_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎤 下载音色: {repo_id} → voices/{voice_name}/")

    try:
        tree = list(list_repo_tree(repo_id, recursive=True))
        model_files = []
        for f in tree:
            name = f.rfilename if hasattr(f, "rfilename") else str(f)
            if name.endswith((".pth", ".index")):
                model_files.append(name)

        if not model_files:
            print("  ⚠ 没有 .pth/.index 文件")
            return False

        print(f"  找到 {len(model_files)} 个文件")
        ok = 0
        for fname in model_files:
            dest = voice_dir / Path(fname).name
            if download_file(repo_id, fname, dest, fname):
                ok += 1

        if ok:
            print(f"  ✅ 已保存到 voices/{voice_name}/")
        return ok > 0
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False


def show_guide():
    print()
    print("=" * 60)
    print("🎤 人声模型下载指南")
    print("=" * 60)
    print("""
下载后放到 voices/ 目录:
  voices/
    ├── 歌手名/
    │   ├── xxx.pth    ← 必须
    │   └── xxx.index  ← 可选 (提升质量)

推荐网站:
  1. weights.gg       — https://weights.gg
  2. voice-models.com — https://voice-models.com (27,900+ 模型)
  3. HuggingFace      — python scripts/download_models.py --voice <repo_id>
  4. B站 / QQ 群      — 中文歌手模型
""")


def main():
    parser = argparse.ArgumentParser(description="AI Voice Cover - 模型下载器")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--voice", type=str, help="HF repo_id")
    parser.add_argument("--voice-name", type=str, default="")
    parser.add_argument("--mirror", action="store_true", help="使用 hf-mirror.com")
    args = parser.parse_args()

    print("\n  🎵 AI Voice Cover - 模型下载器\n")

    if args.mirror:
        setup_mirror()
    else:
        import os
        if not os.environ.get("HF_ENDPOINT"):
            print("  💡 下载慢？试试 --mirror 国内镜像\n")

    ensure_hf_hub()
    print(f"  📁 {BASE_DIR}\n")

    download_base()

    if args.voice:
        download_voice(args.voice, args.voice_name)

    if args.all or not args.voice:
        show_guide()

    print("✅ 完成!\n")


if __name__ == "__main__":
    main()
