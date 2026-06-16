"""Start the QuestCut-AI local Web UI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn


def parse_args():
    parser = argparse.ArgumentParser(description="Run QuestCut-AI local Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host; use 0.0.0.0 for Docker/VPS")
    parser.add_argument("--port", type=int, default=7860, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable reload for development")
    return parser.parse_args()


def main():
    args = parse_args()
    uvicorn.run("src.web.app:app", host=args.host, port=args.port, reload=args.reload, app_dir=str(ROOT))


if __name__ == "__main__":
    main()
