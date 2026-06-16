# QuestCut-AI / AI 智能抠图工具

[中文](#中文) | [English](#english)

---

## 中文

QuestCut-AI 是一个离线优先的 AI 抠图工具，提供 **桌面 GUI**、**本地 Web UI** 和 **Docker/VPS 部署** 三种使用方式。核心推理共用同一套服务层，支持 BiRefNet、BiRefNet Portrait 和 MODNet，适合商品图、人像、Logo、素材批量抠图和透明 PNG 导出。

### 当前状态

- 桌面 GUI：完整编辑工作台，支持批量、画布编辑、撤销/重做、智能裁剪和导出。
- 本地 Web UI：轻量浏览器界面，采用 MiaoCut-like 布局与 Apple Liquid Glass 半透明风格。
- Portable 一键包：可离线运行；GPU Full 包会内置 CUDA/cuDNN runtime，体积较大。

### 主要功能

- **AI 背景移除**：BiRefNet 通用模型、BiRefNet 人像模型、MODNet 人像柔边模型。
- **批量处理**：多图导入、队列预览、状态保留、失败记录、批量 ZIP/保存。
- **编辑增强**：背景色/渐变/图片背景、阴影、边缘锐化/扩展/羽化、智能裁剪。
- **历史操作**：撤销/重做会同步画布位置、遮罩和编辑状态。
- **GPU 加速**：支持 ONNX Runtime CUDA；GPU 初始化失败时自动回退 CPU。
- **双语界面**：English / 简体中文。

### 安装开发环境

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 使用方式

#### 1. 桌面 GUI

```powershell
python run.py
```

#### 2. 本地 Web UI

```powershell
python scripts/run_web.py --host 127.0.0.1 --port 7860
```

打开：

```text
http://127.0.0.1:7860
```

Web UI 支持：

- 拖拽/多选图片。
- 最佳质量、人像硬边、发丝柔边快捷模型切换。
- 图片队列、原图/结果预览。
- 单张处理、批量处理、下载当前、批量 ZIP。
- 明暗模式与 Apple 风格半透明毛玻璃界面。

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

如需公网访问，建议放在 Nginx/Caddy 后面，并加访问控制。模型目录通过 `docker-compose.yml` 挂载：

```text
./models:/app/models:ro
```

### 免安装离线版打包

```powershell
python scripts/build_portable.py --version 1.0.1
```

输出：

```text
dist/release/QuestCut-AI-Portable-v1.0.1.zip
```

说明：

- 压缩包包含 `QuestCut-AI.exe` 和 `models/`，解压后可离线运行。
- 如果打包环境安装了 `onnxruntime-gpu[cuda,cudnn]`，会自动把 CUDA/cuDNN DLL 一起打入包内。
- GPU Full 包约 3.5GB，主要体积来自两个 BiRefNet 模型和 NVIDIA runtime。

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
src/web/                # FastAPI 本地 Web UI 与静态页面
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
- **包很大**：GPU Full 包内置 CUDA/cuDNN、ONNX Runtime CUDA 和两个约 928MiB 的 BiRefNet 模型。
- **首次处理有点卡**：首次加载模型和初始化 CUDA/cuDNN 会慢，后续会复用 session。
- **GPU 报 CUBLAS/CUDA 错误**：程序会自动回退 CPU；需要 GPU 时检查 NVIDIA 驱动。
- **VPS 内存不够**：BiRefNet 模型较重，建议大内存机器；低配优先用 MODNet 或小批量处理。

---

## English

QuestCut-AI is an offline-first AI background remover with three entrypoints: **desktop GUI**, **local Web UI**, and **Docker/VPS deployment**. All entrypoints share the same inference service layer and support BiRefNet, BiRefNet Portrait, and MODNet for product photos, portraits, logos, batch cutouts, and transparent PNG exports.

### Current Status

- Desktop GUI: full editor with batch workflow, canvas editing, undo/redo, smart crop, and export tools.
- Local Web UI: lightweight browser workspace with a MiaoCut-like layout and Apple Liquid Glass styling.
- Portable build: offline-ready; the GPU Full package bundles CUDA/cuDNN runtime and is large by design.

### Features

- **AI background removal** with BiRefNet General, BiRefNet Portrait, and MODNet portrait matting.
- **Batch workflow** with multi-file import, queue preview, persistent state, error records, and batch ZIP/export.
- **Editing tools** for solid/gradient/image backgrounds, shadows, edge refinement, and smart crop.
- **History support** with undo/redo for canvas position, masks, and edit state.
- **GPU acceleration** through ONNX Runtime CUDA with automatic CPU fallback.
- **Bilingual UI**: English and Simplified Chinese.

### Setup

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Usage

#### 1. Desktop GUI

```powershell
python run.py
```

#### 2. Local Web UI

```powershell
python scripts/run_web.py --host 127.0.0.1 --port 7860
```

Open:

```text
http://127.0.0.1:7860
```

Web UI features:

- Drag-and-drop or multi-file picker.
- Quick model modes: best quality, portrait hard edge, and soft hair/edge matting.
- Image queue with original/result previews.
- Process current, process all, download current, and batch ZIP.
- Light/dark mode with Apple-style translucent glass UI.

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

For public access, place it behind Nginx/Caddy with authentication. Models are mounted by `docker-compose.yml`:

```text
./models:/app/models:ro
```

### Portable Offline Build

```powershell
python scripts/build_portable.py --version 1.0.1
```

Output:

```text
dist/release/QuestCut-AI-Portable-v1.0.1.zip
```

Notes:

- The zip includes `QuestCut-AI.exe` and `models/`, so users can unzip and run offline.
- If `onnxruntime-gpu[cuda,cudnn]` is installed in the build environment, CUDA/cuDNN DLLs are bundled automatically.
- The GPU Full package is about 3.5GB, mostly from two BiRefNet models and NVIDIA runtime DLLs.

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
src/web/                # FastAPI local Web UI and static page
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
- **Large package size**: the GPU Full build bundles CUDA/cuDNN, ONNX Runtime CUDA, and two ~928MiB BiRefNet models.
- **First run feels slow**: the first model load and CUDA/cuDNN initialization can take time; later runs reuse sessions.
- **CUBLAS/CUDA GPU errors**: the app falls back to CPU automatically. For GPU mode, verify the NVIDIA driver.
- **Low VPS memory**: BiRefNet is heavy. Use a large-memory server, or prefer MODNet / smaller batches on low-end hosts.
