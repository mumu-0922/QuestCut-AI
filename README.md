# QuestCut-AI / AI 智能抠图工具

[中文](#中文) | [English](#english)

---

## 中文

QuestCut-AI 是一个离线优先的 AI 抠图工具，支持桌面 GUI、本地 Web UI 和 Docker/VPS 部署。核心推理共用同一套服务层，支持 BiRefNet、BiRefNet Portrait 和 MODNet 模型，适合单张抠图、批量处理、透明 PNG 导出和人像柔边处理。

### 主要功能

- **AI 背景移除**：BiRefNet 通用模型、BiRefNet 人像模型、MODNet 人像柔边模型。
- **批量处理**：多图导入、状态保留、失败重试、批量保存。
- **编辑增强**：背景色/渐变/图片背景、阴影、边缘锐化/扩展/羽化、智能裁剪、撤销/重做。
- **GPU 加速**：支持 ONNX Runtime CUDA；GPU 初始化失败时自动回退 CPU。
- **双语界面**：English / 简体中文。
- **三种分发**：免安装离线版、本地网页 UI、Docker/VPS 部署。

### 使用方式

#### 1. 桌面 GUI

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

#### 2. 本地 Web UI

```bash
python scripts/run_web.py --host 127.0.0.1 --port 7860
```

然后浏览器打开：

```text
http://127.0.0.1:7860
```

Web 功能：

- 多图选择和拖拽导入。
- 图片队列切换预览。
- 单张处理、批量处理。
- 下载当前结果，或直接生成批量 ZIP。

API：

```text
GET  /health
GET  /api/models
POST /api/remove-background
POST /api/remove-background-batch
```

#### 3. Docker / VPS

```bash
docker compose up --build
```

默认只绑定本机：

```text
127.0.0.1:7860
```

如需公网访问，建议放在 Nginx/Caddy 后面，并加访问控制。模型目录通过 `docker-compose.yml` 挂载到容器：

```text
./models:/app/models:ro
```

### 免安装离线版打包

```bash
python scripts/build_portable.py --version 1.0.1
```

输出：

```text
dist/release/QuestCut-AI-Portable-v1.0.1.zip
```

压缩包会包含 `QuestCut-AI.exe` 和 `models/`，用户解压后可离线运行。

### 模型文件

ONNX 模型体积较大，不提交到 Git。请按文档下载并放入：

```text
models/rembg/birefnet-general.onnx
models/rembg/birefnet-portrait.onnx
models/modnet/modnet.onnx
```

来源、大小、MD5/SHA256 见：

```text
models/MODEL_SOURCES.md
```

### 项目结构

```text
run.py                  # 桌面应用入口
src/core/               # 模型管理、GPU 检测、背景移除、人像模式
src/services/           # 桌面/Web/Docker 共用抠图服务层
src/web/                # FastAPI 本地 Web UI
src/processing/         # 图像处理、遮罩、批量队列、导出
src/ui/                 # PySide6 窗口、控件、画布、批量面板
src/controllers/        # 批量与导出控制器
src/utils/              # 常量、设置、i18n、校验、license 工具
scripts/                # smoke、Web 启动、portable 打包脚本
tests/                  # 单元与 UI smoke 测试
models/MODEL_SOURCES.md # 模型来源、大小和校验值
```

### 测试

```bash
python3 -m py_compile run.py $(find src -name '*.py') tests/*.py scripts/*.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\smoke_checks.py
```

### 常见问题

- **卡在 0%**：通常是模型缺失或路径不对，检查 `models/` 是否按上面结构放置。
- **GPU 报 CUBLAS/CUDA 错误**：程序会自动回退 CPU；需要 GPU 时检查显卡驱动、CUDA/cuDNN 和 `onnxruntime-gpu`。
- **VPS 内存不够**：BiRefNet 模型约 928MiB/个，部署建议使用大内存机器；低配机器优先用 MODNet 或 CPU 小批量处理。

---

## English

QuestCut-AI is an offline-first AI background remover with a desktop GUI, local Web UI, and Docker/VPS deployment mode. All entrypoints share the same inference service layer and support BiRefNet, BiRefNet Portrait, and MODNet for single-image editing, batch processing, transparent PNG export, and portrait matting.

### Features

- **AI background removal** with BiRefNet General, BiRefNet Portrait, and MODNet portrait matting.
- **Batch workflow** with persistent item state, failed-item retry, and batch export.
- **Editing tools** for solid/gradient/image backgrounds, shadows, edge refinement, smart crop, undo, and redo.
- **GPU acceleration** through ONNX Runtime CUDA with automatic CPU fallback.
- **Bilingual UI**: English and Simplified Chinese.
- **Three delivery modes**: portable offline build, local Web UI, and Docker/VPS deployment.

### Usage

#### 1. Desktop GUI

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

#### 2. Local Web UI

```bash
python scripts/run_web.py --host 127.0.0.1 --port 7860
```

Open:

```text
http://127.0.0.1:7860
```

Web features:

- Multi-file picker and drag-and-drop import.
- Queue-based preview switching.
- Single-image processing and batch processing.
- Download current result or generate a batch ZIP.

API:

```text
GET  /health
GET  /api/models
POST /api/remove-background
POST /api/remove-background-batch
```

#### 3. Docker / VPS

```bash
docker compose up --build
```

The default compose file binds only to:

```text
127.0.0.1:7860
```

For public access, place it behind Nginx/Caddy with authentication. Models are mounted into the container by `docker-compose.yml`:

```text
./models:/app/models:ro
```

### Portable Offline Build

```bash
python scripts/build_portable.py --version 1.0.1
```

Output:

```text
dist/release/QuestCut-AI-Portable-v1.0.1.zip
```

The zip includes `QuestCut-AI.exe` and `models/`, so users can unzip and run offline.

### Model Files

Large ONNX binaries are intentionally excluded from Git. Download them and place them at:

```text
models/rembg/birefnet-general.onnx
models/rembg/birefnet-portrait.onnx
models/modnet/modnet.onnx
```

Source URLs, sizes, MD5, and SHA256 checksums are documented in:

```text
models/MODEL_SOURCES.md
```

### Project Structure

```text
run.py                  # Desktop application launcher
src/core/               # Model manager, GPU helpers, remover, portrait mode
src/services/           # Shared cutout service for desktop/Web/Docker
src/web/                # FastAPI local Web UI
src/processing/         # Image processing, masks, batch queue, export
src/ui/                 # PySide6 windows, widgets, canvas, batch panels
src/controllers/        # Batch and export controllers
src/utils/              # Constants, settings, i18n, validation, license helpers
scripts/                # Smoke, Web launcher, and portable packaging scripts
tests/                  # Unit and UI smoke tests
models/MODEL_SOURCES.md # Model source URLs, sizes, and checksums
```

### Tests

```bash
python3 -m py_compile run.py $(find src -name '*.py') tests/*.py scripts/*.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\smoke_checks.py
```

### Troubleshooting

- **Stuck at 0%**: usually caused by missing model files or a wrong model path. Check the `models/` layout above.
- **CUBLAS/CUDA GPU errors**: the app falls back to CPU automatically. For GPU mode, verify the NVIDIA driver, CUDA/cuDNN runtime, and `onnxruntime-gpu`.
- **Low VPS memory**: BiRefNet is about 928MiB per model. Use a large-memory server, or prefer MODNet / smaller batches on low-end hosts.
