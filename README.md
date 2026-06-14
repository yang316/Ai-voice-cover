# AI Voice Cover

AI 翻唱工具 — 人声分离 + 声音转换 + 混合输出

![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ 功能

- 🎤 **人声分离** — Demucs 自动分离人声和伴奏
- 🔄 **多后端声音转换** — GPT-SoVITS / RVC / ElevenLabs / Fish Audio
- 🎵 **混音输出** — FFmpeg 自动混合生成翻唱音频
- 🧠 **模型训练** — 上传音频自动训练 RVC 人声模型（Demucs 自动提取人声 + HuBERT 特征）
- 🗣️ **TTS 语音合成** — Edge TTS / MiMo 多引擎
- 🖥️ **桌面应用** — Tauri v2 跨平台（~10MB，原生 WebView）
- 🌐 **Web UI** — Vue 3 + Naive UI 暗色主题，中英双语
- 🔍 **GPU 自动检测** — NVIDIA CUDA / AMD ROCm / Intel XPU / Apple MPS

## 🏗️ 架构

```
┌──────────────┐     ┌──────────┐     ┌───────────────┐
│  Frontend    │────→│  FastAPI  │────→│ Celery Worker │
│  (Vue 3)     │     │  Server   │     │   Pipeline    │
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
pip install -e .

# 前端
cd frontend-vue && npm install && cd ..
```

### 3. 下载模型

```bash
# 一键下载基础模型 (HuBERT + RMVPE + RVC v2 预训练 + Demucs)
bash scripts/download_models.sh

# 或用 Python 脚本 (支持 --mirror 国内加速)
python scripts/download_models.py --mirror
```

### 4. 启动服务

```bash
# 启动 Redis
redis-server --daemonize yes

# 启动 Worker
celery -A backend.workers.celery_app worker --loglevel=info &

# 启动 API
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端开发服务器 (另一个终端)
cd frontend-vue && npm run dev
```

访问 http://localhost:5173

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

### 模型训练

上传音频文件即可自动训练 RVC 人声模型：

1. 上传音频（支持带伴奏的歌曲，Demucs 自动提取人声）
2. 自动切片（10 秒片段，8 秒重叠）
3. HuBERT 特征提取 + F0 音高提取
4. 训练模型，进度实时显示
5. 完成后自动保存到 `voices/` 目录

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/covers` | 提交翻唱任务 |
| GET | `/api/v1/covers/{id}` | 查询任务状态 |
| GET | `/api/v1/covers/{id}/download` | 下载翻唱结果 |
| POST | `/api/v1/train` | 提交训练任务 |
| GET | `/api/v1/train/{id}` | 查询训练进度 |
| GET | `/api/v1/health` | 健康检查 + GPU 信息 |
| GET | `/api/v1/voices` | 列出已安装音色模型 |
| POST | `/api/v1/tts` | TTS 语音合成 |
| POST | `/api/v1/models/download-base` | 一键下载基础模型 |
| POST | `/api/v1/models/download-voice` | 下载 HuggingFace 音色模型 |

## 📁 项目结构

```
ai-voice-cover/
├── backend/
│   ├── api/              # API 路由
│   │   ├── routes.py     # 翻唱任务 API
│   │   ├── train_routes.py  # 模型训练 API
│   │   ├── tts_routes.py    # TTS 语音合成
│   │   ├── voice_routes.py  # 音色管理
│   │   └── model_routes.py  # 模型下载
│   ├── backends/         # 计算后端
│   │   ├── local_gpu.py  # RVC 本地推理
│   │   ├── gpt_sovits.py # GPT-SoVITS API
│   │   └── cloud_api.py  # ElevenLabs / Fish Audio
│   ├── core/             # 核心模块
│   │   ├── pipeline.py   # 翻唱流水线
│   │   ├── separator.py  # Demucs 人声分离
│   │   ├── rvc_infer.py  # RVC 推理
│   │   └── device.py     # GPU 自动检测
│   ├── training/         # 模型训练
│   │   └── trainer.py    # RVC 训练器
│   ├── tts/              # TTS 引擎
│   │   ├── edge_tts_provider.py
│   │   └── mimo_provider.py
│   ├── workers/          # Celery 异步任务
│   └── config.py         # 配置管理
├── frontend-vue/         # Vue 3 前端
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── components/   # UI 组件
│   │   ├── stores/       # Pinia 状态管理
│   │   └── composables/  # 组合式函数
│   └── package.json
├── src-tauri/            # Tauri v2 桌面应用
├── scripts/
│   ├── download_models.py      # 模型下载器
│   ├── download_models.sh      # 一键下载脚本
│   ├── build-desktop.sh        # 桌面应用构建
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
git tag v0.2.0 && git push origin v0.2.0
```

构建产物：
- 🐧 Linux: `.AppImage` + `.deb`
- 🍎 macOS: `.dmg` (Apple Silicon)
- 🪟 Windows: `.msi` + `.exe`

## 📄 License

MIT
