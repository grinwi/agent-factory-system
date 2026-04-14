#!/usr/bin/env python3
"""Launch the local FastAPI app from the project root."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.bootstrap_support import (  # noqa: E402
    parse_env_file,
    validate_runtime_env,
    venv_python_path,
)

ENV_PATH = PROJECT_ROOT / ".env"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local manufacturing analytics app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    python_bin = venv_python_path(PROJECT_ROOT)
    if not python_bin.exists():
        print("The local environment is not ready yet.")
        print("Run the setup wizard first:")
        if sys.platform == "win32":
            print("  setup.bat")
        else:
            print("  ./setup.command")
        return 1

    env_values = parse_env_file(ENV_PATH)
    problems = validate_runtime_env(env_values)
    if problems:
        print("The local .env file is incomplete:")
        for problem in problems:
            print(f"  - {problem}")
        print("\nRun the setup wizard to finish configuration.")
        return 1

    url = f"http://{args.host}:{args.port}/"
    print(f"Starting Manufacturing Analytics at {url}")
    if not args.no_browser:
        threading.Thread(target=_open_browser_later, args=(url,), daemon=True).start()

    launch_env = os.environ.copy()
    launch_env.update(env_values)
    return subprocess.call(
        [
            str(python_bin),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        cwd=PROJECT_ROOT,
        env=launch_env,
    )


def _open_browser_later(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


if __name__ == "__main__":
    raise SystemExit(main())
