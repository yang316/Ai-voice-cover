# Gitea + Runner 部署指南

## 1. ECS 上部署 Gitea

```bash
# SSH 到 ECS
ssh root@8.137.82.33

# 创建目录
mkdir -p /opt/gitea && cd /opt/gitea

# 拷贝 docker-compose.yml 到这个目录
# 然后启动
docker compose up -d

# 访问 http://8.137.82.33:3000 完成初始设置
# 注册账号，创建仓库 ai-voice-cover
```

## 2. 本地 Fedora 安装 Runner

```bash
# 下载 act_runner
curl -L -o act_runner https://github.com/nektos/act/releases/latest/download/act_runner-linux-amd64
chmod +x act_runner
sudo mv act_runner /usr/local/bin/

# 或者用 Gitea 官方 runner
curl -L -o gitea-runner https://github.com/gitea/act_runner/releases/latest/download/act_runner-linux-amd64
chmod +x gitea-runner
sudo mv gitea-runner /usr/local/bin/
```

### 注册 Runner

```bash
# 1. 在 Gitea Web UI: 仓库设置 → Actions → Runners → 获取 registration token
# 2. 注册
gitea-runner register \
  --instance http://8.137.82.33:3000 \
  --token <registration-token> \
  --name fedora-local \
  --labels ubuntu-latest:docker://node:20-bookworm

# 3. 启动 runner
gitea-runner daemon --config .runner
```

## 3. Gitea Actions Workflow

把 `.github/workflows/build-desktop.yml` 复制为：
`.gitea/workflows/build-desktop.yml`

Gitea Actions 兼容 GitHub Actions 语法，workflow 文件基本不用改。

## 4. 推送代码到 Gitea

```bash
# 添加 Gitea 为 remote
git remote add gitea http://8.137.82.33:3000/cola/ai-voice-cover.git

# 推送
git push gitea main
git push gitea v0.3.5

# Tag 推送后自动触发构建
```

## 注意事项

- ECS 2G 内存不够跑 Tauri 构建，Runner 建议跑在你本机
- Runner 用 Docker 模式执行 job，需要安装 Docker
- 构建产物可以在 Gitea Releases 页面下载
