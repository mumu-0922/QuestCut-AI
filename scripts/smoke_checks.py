"""Run QuestCut-AI smoke checks without requiring pytest."""
from __future__ import annotations

import os
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compile_sources() -> None:
    for path in [ROOT / 'run.py', *sorted((ROOT / 'src').rglob('*.py'))]:
        py_compile.compile(str(path), doraise=True)


def run_unittest() -> None:
    env = os.environ.copy()
    env.setdefault('QT_QPA_PLATFORM', 'offscreen')
    subprocess.run(
        [sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-v'],
        cwd=str(ROOT),
        env=env,
        check=True,
    )


if __name__ == '__main__':
    compile_sources()
    run_unittest()
    print('smoke checks ok')
