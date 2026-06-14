#!/bin/bash
# AI Voice Cover - One-click model downloader
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "============================================"
echo "  AI Voice Cover - 模型下载"
echo "============================================"
echo ""

# 1. Download base models (HuBERT + RMVPE + RVC pretrained)
echo "[1/2] 下载基础模型..."
python3 "$SCRIPT_DIR/download_models.py" --mirror "$@"
echo ""

# 2. Download Demucs model
echo "[2/2] 下载 Demucs 人声分离模型..."
python3 -c "from demucs.pretrained import get_model; get_model('htdemucs')" 2>/dev/null \
    && echo "  ✓ Demucs htdemucs 模型已就绪" \
    || echo "  ⚠ Demucs 下载失败，请确保已安装 demucs: pip install demucs"
echo ""

echo "============================================"
echo "  ✅ 模型下载完成!"
echo "============================================"
echo ""
echo "  基础模型: $PROJECT_DIR/assets/"
echo "  音色模型: $PROJECT_DIR/voices/"
echo ""
