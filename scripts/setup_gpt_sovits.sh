#!/usr/bin/env bash
# AI Voice Cover - GPT-SoVITS Setup Script
# Downloads, installs, and manages GPT-SoVITS as an integrated component.
#
# Usage:
#   bash scripts/setup_gpt_sovits.sh install    # Clone + install deps
#   bash scripts/setup_gpt_sovits.sh start      # Start API server
#   bash scripts/setup_gpt_sovits.sh stop       # Stop API server
#   bash scripts/setup_gpt_sovits.sh status     # Check if running
#   bash scripts/setup_gpt_sovits.sh download   # Download pretrained models

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GPT_DIR="$PROJECT_DIR/third_party/GPT-SoVITS"
GPT_PORT=9880
GPT_PID_FILE="$PROJECT_DIR/.gpt_sovits.pid"
GPT_LOG="$PROJECT_DIR/logs/gpt_sovits.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

cmd_install() {
    info "Setting up GPT-SoVITS..."

    # Check git
    if ! command -v git &>/dev/null; then
        err "git not found. Install: sudo dnf install git"
        exit 1
    fi

    # Clone or update
    if [ -d "$GPT_DIR" ]; then
        info "GPT-SoVITS already cloned at $GPT_DIR"
        cd "$GPT_DIR"
        git pull --ff-only 2>/dev/null || warn "Pull failed, using existing version"
    else
        info "Cloning GPT-SoVITS..."
        mkdir -p "$PROJECT_DIR/third_party"
        git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS.git "$GPT_DIR"
    fi

    cd "$GPT_DIR"

    # Install Python deps
    info "Installing Python dependencies..."
    if [ -d "$PROJECT_DIR/.venv" ]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    fi

    pip install -q -r requirements.txt 2>/dev/null || {
        warn "requirements.txt install failed, trying minimal install..."
        pip install -q fastapi uvicorn pydantic httpx soundfile numpy torch torchaudio
    }

    # Install GPT-SoVITS package
    pip install -q -e . 2>/dev/null || true

    ok "GPT-SoVITS installed at: $GPT_DIR"
    info "Run: bash scripts/setup_gpt_sovits.sh download  (to get pretrained models)"
    info "Run: bash scripts/setup_gpt_sovits.sh start     (to start API server)"
}

cmd_download() {
    info "Downloading GPT-SoVITS pretrained models..."

    cd "$GPT_DIR"

    # Download pretrained models using huggingface_hub
    python3 -c "
import os, sys
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
try:
    from huggingface_hub import snapshot_download
    print('Downloading GPT-SoVITS pretrained models...')
    snapshot_download(
        'lj1995/GPT-SoVITS',
        local_dir='pretrained_models',
        allow_patterns=['*.pth', '*.pt', '*.bin', '*.json', '*.yaml'],
        local_dir_use_symlinks=False,
    )
    print('Done!')
except Exception as e:
    print(f'Error: {e}')
    print('Try: HF_ENDPOINT=https://hf-mirror.com bash scripts/setup_gpt_sovits.sh download')
    sys.exit(1)
" 2>&1

    ok "Pretrained models downloaded"
}

cmd_start() {
    mkdir -p "$PROJECT_DIR/logs"

    # Check if already running
    if [ -f "$GPT_PID_FILE" ] && kill -0 "$(cat "$GPT_PID_FILE")" 2>/dev/null; then
        warn "GPT-SoVITS already running (PID: $(cat "$GPT_PID_FILE"))"
        return 0
    fi

    if [ ! -d "$GPT_DIR" ]; then
        err "GPT-SoVITS not installed. Run: bash scripts/setup_gpt_sovits.sh install"
        exit 1
    fi

    cd "$GPT_DIR"

    # Activate venv if exists
    if [ -d "$PROJECT_DIR/.venv" ]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    fi

    # Find config file
    CONFIG_FILE=""
    if [ -f "GPT_SoVITS/configs/tts_infer.yaml" ]; then
        CONFIG_FILE="GPT_SoVITS/configs/tts_infer.yaml"
    fi

    info "Starting GPT-SoVITS API on port $GPT_PORT..."

    export PYTHONPATH="$GPT_DIR:$GPT_DIR/GPT_SoVITS:${PYTHONPATH:-}"

    if [ -n "$CONFIG_FILE" ]; then
        nohup python api_v2.py -a 127.0.0.1 -p "$GPT_PORT" -c "$CONFIG_FILE" \
            > "$GPT_LOG" 2>&1 &
    else
        nohup python api_v2.py -a 127.0.0.1 -p "$GPT_PORT" \
            > "$GPT_LOG" 2>&1 &
    fi

    PID=$!
    echo "$PID" > "$GPT_PID_FILE"

    # Wait for startup
    info "Waiting for GPT-SoVITS to start..."
    for i in $(seq 1 30); do
        if curl -s "http://127.0.0.1:$GPT_PORT/" >/dev/null 2>&1; then
            ok "GPT-SoVITS API running on http://127.0.0.1:$GPT_PORT (PID: $PID)"
            return 0
        fi
        sleep 1
    done

    warn "GPT-SoVITS may still be starting. Check logs: $GPT_LOG"
}

cmd_stop() {
    if [ -f "$GPT_PID_FILE" ]; then
        PID=$(cat "$GPT_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            rm -f "$GPT_PID_FILE"
            ok "GPT-SoVITS stopped (PID: $PID)"
        else
            rm -f "$GPT_PID_FILE"
            warn "GPT-SoVITS was not running"
        fi
    else
        warn "No PID file found"
        # Try to find and kill by port
        PID=$(lsof -ti:$GPT_PORT 2>/dev/null || true)
        if [ -n "$PID" ]; then
            kill "$PID" 2>/dev/null || true
            ok "Killed process on port $GPT_PORT"
        fi
    fi
}

cmd_status() {
    if [ -f "$GPT_PID_FILE" ] && kill -0 "$(cat "$GPT_PID_FILE")" 2>/dev/null; then
        PID=$(cat "$GPT_PID_FILE")
        ok "GPT-SoVITS running (PID: $PID, Port: $GPT_PORT)"
        curl -s "http://127.0.0.1:$GPT_PORT/" >/dev/null 2>&1 && \
            echo "  API responding ✓" || echo "  API not responding ✗"
    else
        warn "GPT-SoVITS not running"
    fi
}

# Main
case "${1:-help}" in
    install)  cmd_install ;;
    download) cmd_download ;;
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    status)   cmd_status ;;
    restart)  cmd_stop; sleep 1; cmd_start ;;
    *)
        echo "Usage: $0 {install|download|start|stop|restart|status}"
        echo ""
        echo "  install   Clone and install GPT-SoVITS"
        echo "  download  Download pretrained models"
        echo "  start     Start API server on port $GPT_PORT"
        echo "  stop      Stop API server"
        echo "  restart   Restart API server"
        echo "  status    Check if running"
        ;;
esac
