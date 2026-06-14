# AI Voice Cover

AI 翻唱工具 — 人声分离 + 声音转换 + 混合输出

## 功能

- 🎤 **人声分离** — Demucs 分离人声和伴奏
- 🔄 **声音转换** — 支持多种后端（本地GPU / ElevenLabs / Fish Audio）
- 🎵 **混音输出** — 自动混合生成翻唱音频
- 🌐 **Web UI** — 暗色主题现代化界面
- 🐳 **Docker** — 一键部署

## 架构

```
Frontend (HTML/JS) → FastAPI → Celery Worker → Pipeline
                                              ├── Demucs (人声分离)
                                              ├── RVC / API (声音转换)
                                              └── FFmpeg (混音)
```

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
docker compose up --build
```

访问 http://localhost:8000

### 方式二：本地运行

```bash
# 安装依赖
pip install -e .

# 启动 Redis
redis-server --daemonize yes

# 启动 Worker
celery -A backend.workers.celery_app worker --loglevel=info &

# 启动 API
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/covers` | 提交翻唱任务 |
| GET | `/api/v1/covers/{id}` | 查询任务状态 |
| GET | `/api/v1/covers/{id}/download` | 下载翻唱结果 |
| GET | `/api/v1/voices` | 列出可用音色 |
| GET | `/api/v1/health` | 健康检查 |

## 计算后端

| 后端 | 说明 | 需要 |
|------|------|------|
| `local` | 本地 GPU 推理 (RVC) | CUDA GPU |
| `elevenlabs` | ElevenLabs API | API Key |
| `fish_audio` | Fish Audio API | API Key |

## 项目结构

```
ai-voice-cover/
├── backend/
│   ├── api/            # API 路由和数据模型
│   ├── backends/       # 计算后端（本地/云端）
│   ├── core/           # 核心 Pipeline
│   ├── workers/        # Celery 异步任务
│   ├── config.py       # 配置
│   └── main.py         # FastAPI 入口
├── frontend/           # Web 前端
├── voices/             # 音色模型
├── uploads/            # 上传文件
├── output/             # 输出文件
├── scripts/            # 运行脚本
├── docker-compose.yml  # Docker 编排
└── README.md
```

## 开发路线

- [x] Phase 1: 核心 Pipeline + 多后端架构
- [ ] Phase 2: RVC 模型推理集成
- [ ] Phase 3: 音色模型管理（上传/训练）
- [ ] Phase 4: 用户系统和任务历史
- [ ] Phase 5: 部署优化和 GPU 调度
