# CLAUDE.md

Guidance for working in the AI Voice Cover repository.

## Project overview

AI Voice Cover — 人声分离 + 声音转换 + 混合输出. A desktop app that bundles a
Python (FastAPI) backend behind a Tauri 2 + Vue 3 shell.

- **`backend/`** — FastAPI app (`backend.main:app`). Routers load defensively:
  ML features degrade gracefully when their deps are missing (see
  `_try_load_router` in `backend/main.py`). **Do not modify `backend/core/`** —
  that is the ML inference core.
- **`frontend-vue/`** — Vue 3 + Vite + naive-ui frontend. Built output in
  `frontend-vue/dist/` is served both by Tauri (`frontendDist`) and by the
  backend's `StaticFiles` mount.
- **`src-tauri/`** — Tauri 2 Rust shell. `src/lib.rs` spawns the Python sidecar
  on startup and waits for the backend on port `9527`.
- **`scripts/sidecar-launcher.py`** — entry point the Tauri shell runs. Finds an
  interpreter, bootstraps pip, installs core deps on first run, then starts
  uvicorn.

## Architecture notes

- Backend port is hardcoded to `9527` (`BACKEND_PORT` in `src-tauri/src/lib.rs`,
  honored via `AVC_PORT`).
- Two dependency tiers: `scripts/requirements.txt` (core — installed on first
  launch) and `scripts/requirements-ml.txt` (large ML deps — installed on demand
  by the `ml` routes).
- **Windows** ships an embedded CPython (downloaded in CI); **Linux/macOS** rely
  on system Python 3.11–3.13 found on `PATH`.

## Build & verify

```bash
# Frontend (the key CI step)
cd frontend-vue && npm ci && npm run build

# Full desktop build (downloads embedded Python on Windows)
./scripts/build-desktop.sh [linux|mac|windows|all]
```

Always re-validate after edits:
- YAML: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-desktop.yml'))"`
- JSON: `python3 -c "import json; json.load(open('src-tauri/tauri.conf.json'))"`
- Python: `python3 -m py_compile scripts/sidecar-launcher.py`
- Shell: `bash -n scripts/build-desktop.sh`

## Versioning

Version must stay in sync across **four** places (currently `0.3.5`):
`package.json`, `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`,
`src-tauri/Cargo.lock`. The `Build Desktop App` workflow extracts the version
from a `v*` git tag and rewrites the first three (Cargo.lock auto-updates during
`cargo build`). Keep them aligned when bumping manually.

## CI/CD

`.github/workflows/build-desktop.yml` builds Linux (AppImage/deb), macOS (dmg),
and Windows (msi/nsis) on `v*` tags, then publishes a GitHub release.

The sidecar bundle is assembled fresh in CI (`Prepare sidecar` step). Tauri
bundles it via the `sidecar/**/*` resource glob in `tauri.conf.json` — use a
**recursive** glob so newly added backend subpackages are always included.
Tauri's glob skips dotfiles, so the Linux/macOS `python/.placeholder` is
intentionally not bundled.

## Conventions

- Don't delete existing functionality — fix and optimize only.
- `src-tauri/sidecar/`, `dist/`, `target/`, `node_modules/`, `.venv/` are
  git-ignored build artifacts; never commit them.
- Match the surrounding code's style and comment density.
