"""Build a portable QuestCut-AI Windows zip.

The script intentionally builds an onedir app instead of an installer. It copies
`models/` next to `QuestCut-AI.exe` so the app can run offline after unzip.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

APP_NAME = "QuestCut-AI"
DEFAULT_VERSION = "1.0.1"
REQUIRED_MODEL_FILES = [
    Path("models/rembg/birefnet-general.onnx"),
    Path("models/rembg/birefnet-portrait.onnx"),
    Path("models/modnet/modnet.onnx"),
]


def parse_args():
    parser = argparse.ArgumentParser(description="Build portable QuestCut-AI release zip")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Version string used in zip name")
    parser.add_argument("--skip-model-check", action="store_true", help="Allow building without bundled ONNX models")
    parser.add_argument("--no-zip", action="store_true", help="Build dist folder but do not create zip")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required for portable builds. Install it with:\n"
            "  python -m pip install pyinstaller\n"
        ) from exc


def ensure_models(root: Path, *, skip: bool = False):
    missing = [str(path) for path in REQUIRED_MODEL_FILES if not (root / path).is_file()]
    if missing and not skip:
        raise SystemExit(
            "Missing bundled model files:\n  "
            + "\n  ".join(missing)
            + "\nSee models/MODEL_SOURCES.md for download URLs and checksums."
        )
    return missing


def run_pyinstaller(root: Path):
    build_dir = root / "build" / "pyinstaller"
    dist_dir = root / "dist"
    work_dir = dist_dir / APP_NAME
    if work_dir.exists():
        shutil.rmtree(work_dir)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "run.py",
    ]
    subprocess.run(cmd, cwd=root, check=True)
    exe = work_dir / f"{APP_NAME}.exe"
    if not exe.exists():
        raise SystemExit(f"Expected executable not found: {exe}")
    return work_dir


def copy_models(root: Path, work_dir: Path):
    source = root / "models"
    target = work_dir / "models"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("MODEL_SOURCES.md"))
    shutil.copy2(source / "MODEL_SOURCES.md", target / "MODEL_SOURCES.md")


def write_release_notes(work_dir: Path, version: str):
    (work_dir / "README_PORTABLE.txt").write_text(
        f"{APP_NAME} Portable v{version}\n"
        "\n"
        "How to use:\n"
        f"1. Double-click {APP_NAME}.exe.\n"
        "2. Drop an image into the app.\n"
        "3. Click Remove Background and save the result.\n"
        "\n"
        "This portable build bundles ONNX models under ./models and works offline.\n"
        "Do not remove the models folder.\n",
        encoding="utf-8",
    )


def create_zip(root: Path, work_dir: Path, version: str) -> Path:
    release_dir = root / "dist" / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    zip_path = release_dir / f"{APP_NAME}-Portable-v{version}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in work_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(work_dir.parent))
    return zip_path


def main():
    args = parse_args()
    root = repo_root()
    ensure_pyinstaller()
    missing = ensure_models(root, skip=args.skip_model_check)
    work_dir = run_pyinstaller(root)
    if (root / "models").exists():
        copy_models(root, work_dir)
    write_release_notes(work_dir, args.version)
    if args.no_zip:
        print(f"Portable folder ready: {work_dir}")
    else:
        zip_path = create_zip(root, work_dir, args.version)
        print(f"Portable zip ready: {zip_path}")
    if missing:
        print("WARNING: built without some model files:")
        for item in missing:
            print(f"  {item}")


if __name__ == "__main__":
    main()
