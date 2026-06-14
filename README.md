# AI Voice Cover

AI 翻唱工具 — 人声分离 + 声音转换 + 混合输出

![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ 功能

- 🎤 **人声分离** — Demucs 自动分离人声和伴奏
- 🔄 **多后端声音转换** — GPT-SoVITS / RVC / ElevenLabs / Fish Audio
- 🎵 **混音输出** — FFmpeg 自动混合生成翻唱音频
- 🖥️ **桌面应用** — Tauri v2 跨平台（~10MB，原生 WebView）
- 🌐 **Web UI** — 暗色主题，Glass morphism，中英双语
- 🔍 **GPU 自动检测** — NVIDIA CUDA / AMD ROCm / Intel XPU / Apple MPS

## 🏗️ 架构

```
┌──────────────┐     ┌──────────┐     ┌───────────────┐
│  Frontend    │────→│  FastAPI  │────→│ Celery Worker │
│  (HTML/JS)   │     │  Server   │     │   Pipeline    │
└──────────────┘     └──────────┘     └───────┬───────┘
                                              │
                   ┌──────────────────────────┼────────────────────┐
                   │                          │                    │
            ┌──────┴──────┐          ┌────────┴────────┐    ┌─────┴─────┐
            │   Demucs     │          │  Voice Convert   │    │  FFmpeg   │
            │ (人声分离)    │          │  (声音转换)       │    │  (混音)   │
            └─────────────┘          └────────┬────────┘    └───────────┘
                                              │
                          ┌───────────┬───────┴──────┬──────────────┐
                          │           │              │              │
                       GPT-SoVITS    RVC      ElevenLabs      Fish Audio
                       (本地/最佳)  (本地)      (云端)          (云端)
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yang316/Ai-voice-cover.git
cd Ai-voice-cover
```

### 2. 安装依赖

```bash
# Python 虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" "celery[redis]" redis pydantic pydantic-settings \
    python-multipart httpx soundfile numpy torch torchaudio demucs

# Node.js (前端/桌面应用)
npm install
```

### 3. 下载模型

```bash
# 一键下载基础模型 (HuBERT + RMVPE + RVC v2 预训练)
python scripts/download_models.py --mirror

# GPT-SoVITS 安装 (可选，中文效果最好)
bash scripts/setup_gpt_sovits.sh install
bash scripts/setup_gpt_sovits.sh download
```

### 4. 启动服务

```bash
# 启动 Redis
redis-server --daemonize yes

# 启动 Worker
celery -A backend.workers.celery_app worker --loglevel=info &

# 启动 API
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 GPT-SoVITS (可选)
bash scripts/setup_gpt_sovits.sh start
```

访问 http://localhost:8000

### 5. 桌面应用开发

```bash
npm run tauri:dev    # 开发模式
npm run tauri:build  # 构建安装包
```

## 🔌 计算后端

| 后端 | 说明 | 要求 | 效果 |
|------|------|------|------|
| **GPT-SoVITS** | 开源 TTS，本地部署 | GPU (推荐) | ⭐⭐⭐⭐⭐ 中文最佳 |
| **RVC** | 本地声音转换 | GPU (4GB+) | ⭐⭐⭐⭐ |
| **ElevenLabs** | 英文最强云端 API | API Key | ⭐⭐⭐⭐ |
| **Fish Audio** | 中文最强云端 API | API Key | ⭐⭐⭐⭐ |

### GPT-SoVITS（推荐）

```bash
# 一键安装
bash scripts/setup_gpt_sovits.sh install

# 下载预训练模型
bash scripts/setup_gpt_sovits.sh download

# 启动 API 服务 (端口 9880)
bash scripts/setup_gpt_sovits.sh start

# 管理
bash scripts/setup_gpt_sovits.sh status   # 查看状态
bash scripts/setup_gpt_sovits.sh stop     # 停止
bash scripts/setup_gpt_sovits.sh restart  # 重启
```

### RVC 人声模型下载

模型文件放到 `voices/` 目录：

```bash
# 从 HuggingFace 下载 (国内用 --mirror)
python scripts/download_models.py --voice <repo_id> --mirror

# 手动下载
# 1. voice-models.com — https://voice-models.com (27,900+ 模型)
# 2. HuggingFace 镜像 — https://hf-mirror.com/models?search=rvc
# 3. B站 / QQ 群 — 中文歌手模型
```

目录结构：
```
voices/
  ├── 歌手名/
  │   ├── xxx.pth    ← 模型权重 (必须)
  │   └── xxx.index  ← FAISS 索引 (可选，提升质量)
```

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/covers` | 提交翻唱任务 |
| GET | `/api/v1/covers/{id}` | 查询任务状态 |
| GET | `/api/v1/covers/{id}/download` | 下载翻唱结果 |
| GET | `/api/v1/health` | 健康检查 + GPU 信息 |
| GET | `/api/v1/voices` | 列出已安装音色模型 |
| POST | `/api/v1/models/download-base` | 一键下载基础模型 |
| POST | `/api/v1/models/download-voice` | 下载 HuggingFace 音色模型 |

## 📁 项目结构

```
ai-voice-cover/
├── backend/
│   ├── api/              # API 路由
│   │   ├── routes.py     # 翻唱任务 API
│   │   ├── voice_routes.py  # 音色管理
│   │   ├── model_routes.py  # 模型下载
│   │   └── hf_routes.py  # HuggingFace 搜索
│   ├── backends/         # 计算后端
│   │   ├── local_gpu.py  # RVC 本地推理
│   │   ├── gpt_sovits.py # GPT-SoVITS API
│   │   └── cloud_api.py  # ElevenLabs / Fish Audio
│   ├── core/             # 核心模块
│   │   ├── pipeline.py   # 翻唱流水线
│   │   ├── separator.py  # Demucs 人声分离
│   │   ├── rvc_infer.py  # RVC 推理
│   │   └── device.py     # GPU 自动检测
│   ├── workers/          # Celery 异步任务
│   └── config.py         # 配置管理
├── frontend/
│   └── index.html        # 单文件 Web UI
├── src-tauri/            # Tauri v2 桌面应用
├── scripts/
│   ├── download_models.py      # 模型下载器
│   └── setup_gpt_sovits.sh     # GPT-SoVITS 安装管理
├── third_party/          # 第三方工具 (GPT-SoVITS 等)
├── voices/               # 音色模型
├── assets/               # 基础模型 (HuBERT, RMVPE)
└── docker-compose.yml
```

## 🖥️ 桌面应用

基于 Tauri v2 构建，支持 Linux / macOS / Windows：

```bash
# 手动构建
npm run tauri:build

# GitHub Actions 自动构建 (推送 tag 触发)
git tag v0.1.0 && git push origin v0.1.0
```

构建产物：
- 🐧 Linux: `.AppImage` + `.deb`
- 🍎 macOS: `.dmg` (Apple Silicon)
- 🪟 Windows: `.msi` + `.exe`

## 🛠️ 开发路线

- [x] Phase 1: 核心 Pipeline + 多后端架构
- [x] Phase 2: RVC 模型推理 + GPU 自动检测
- [x] Phase 3: GPT-SoVITS 集成 + 云端 API
- [x] Phase 4: Tauri 桌面应用 + GitHub Actions CI/CD
- [ ] Phase 5: 音色模型训练 (前端 UI)
- [ ] Phase 6: 部署优化和 GPU 调度

## 📄 License

MIT
