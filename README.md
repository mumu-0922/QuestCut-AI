# QuestCut-AI / AI 智能抠图工具

[中文](#中文) | [English](#english)

---

## 中文

QuestCut-AI 是一个基于 Python / PySide6 的桌面端 AI 抠图工具，支持单张与批量移除背景、透明 PNG 快速保存、背景/阴影/边缘/位置调整，以及简体中文和英文界面切换。

### 功能特性

- AI 背景移除：BiRefNet 通用模型、BiRefNet 人像模型、MODNet 人像柔边模型。
- 批量处理：支持多图导入、处理状态保留、失败重试和批量保存。
- 编辑能力：背景色/渐变/图片背景、阴影、边缘锐化/扩展/羽化、智能裁剪、撤销/重做。
- GPU 加速：支持 ONNX Runtime CUDA，GPU 初始化失败时自动回退 CPU。
- 双语界面：English / 简体中文。

### 项目结构

```text
run.py                  # 应用入口
src/core/               # 模型管理、GPU 检测、背景移除、人像模式
src/processing/         # 图像处理、遮罩、批量队列、导出
src/ui/                 # PySide6 窗口、控件、画布、批量面板
src/controllers/        # 批量与导出控制器
src/utils/              # 常量、设置、i18n、校验、license 工具
tests/                  # 单元与 UI smoke 测试
models/MODEL_SOURCES.md # 模型来源、大小和校验值
```

### 安装与运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### 测试

```bash
python3 -m py_compile run.py $(find src -name '*.py') tests/*.py scripts/smoke_checks.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\smoke_checks.py
```

### 模型文件

ONNX 模型体积较大，不直接提交到 Git。当前模型来源、文件大小、MD5/SHA256 见：

```text
models/MODEL_SOURCES.md
```

如需打包离线版，请把模型放入：

```text
models/rembg/birefnet-general.onnx
models/rembg/birefnet-portrait.onnx
models/modnet/modnet.onnx
```

---

## English

QuestCut-AI is a Python / PySide6 desktop application for AI-powered background removal. It supports single-image and batch processing, transparent PNG quick save, background/shadow/edge/position editing, and runtime language switching between English and Simplified Chinese.

### Features

- AI background removal with BiRefNet General, BiRefNet Portrait, and MODNet portrait matting.
- Batch workflow with persistent item state, retry for failed items, and batch export.
- Editing tools for solid/gradient/image backgrounds, shadows, edge refinement, smart crop, undo, and redo.
- GPU acceleration through ONNX Runtime CUDA with automatic CPU fallback.
- Bilingual UI: English and Simplified Chinese.

### Project Structure

```text
run.py                  # Application launcher
src/core/               # Model manager, GPU helpers, remover, portrait mode
src/processing/         # Image processing, masks, batch queue, export
src/ui/                 # PySide6 windows, widgets, canvas, batch panels
src/controllers/        # Batch and export controllers
src/utils/              # Constants, settings, i18n, validation, license helpers
tests/                  # Unit and UI smoke tests
models/MODEL_SOURCES.md # Model source URLs, sizes, and checksums
```

### Install and Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Tests

```bash
python3 -m py_compile run.py $(find src -name '*.py') tests/*.py scripts/smoke_checks.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\smoke_checks.py
```

### Model Files

Large ONNX model binaries are intentionally excluded from Git. See the source URLs, sizes, MD5, and SHA256 checksums in:

```text
models/MODEL_SOURCES.md
```

For an offline build, place the model files at:

```text
models/rembg/birefnet-general.onnx
models/rembg/birefnet-portrait.onnx
models/modnet/modnet.onnx
```

### Packaging

The Windows installer script is `install_script.iss`. Build `QuestCut-AI.exe` first, ensure `models/` exists beside the build input, then compile the installer with Inno Setup.

---

## Distribution Roadmap / 分发路线

QuestCut-AI is designed to support three delivery modes from the same inference core:

1. **Portable desktop build / 免安装桌面版**
   - Build command: `python scripts/build_portable.py --version 1.0.1`
   - Output: `dist/release/QuestCut-AI-Portable-v1.0.1.zip`
   - The zip includes `QuestCut-AI.exe` and `models/`, so users can unzip and run offline.

2. **Local Web UI / 本地网页 UI**
   - Planned shape: FastAPI backend + browser UI on `http://127.0.0.1:7860`.
   - It will reuse `src/services/cutout_service.py` instead of duplicating inference logic.

3. **Docker / VPS deployment / Docker 部署**
   - Planned shape: Dockerfile + docker-compose for users with large-memory VPS or GPU servers.
   - The same web backend will be used; deployment must enforce upload size, file type, timeout, and temporary-file cleanup limits.

Current shared inference boundary:

```text
src/services/cutout_service.py
```
