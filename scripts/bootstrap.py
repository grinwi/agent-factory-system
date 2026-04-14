#!/usr/bin/env python3
"""Interactive bootstrap wizard for local BYOK setup."""

from __future__ import annotations

import getpass
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.bootstrap_support import (  # noqa: E402
    build_env_values,
    get_provider_config,
    parse_env_file,
    render_env_file,
    validate_runtime_env,
    venv_python_path,
)

ENV_PATH = PROJECT_ROOT / ".env"


def main() -> int:
    print("Manufacturing Analytics Local Setup")
    print("This wizard creates a local Python environment, installs dependencies,")
    print("and stores your provider key only in this folder's .env file.\n")
    existing_env = parse_env_file(ENV_PATH)

    selected_provider = _prompt_provider(existing_env.get("LLM_PROVIDER"))
    provider_config = get_provider_config(selected_provider)
    default_model = (
        existing_env.get(provider_config.model_env)
        or existing_env.get("LLM_MODEL")
        or provider_config.default_model
    )

    masked_hint = _mask_secret(existing_env.get(provider_config.api_key_env, ""))
    api_key_prompt = f"{provider_config.label} API key"
    if masked_hint:
        api_key_prompt += f" (press Enter to keep {masked_hint})"
    api_key = getpass.getpass(f"{api_key_prompt}: ").strip()
    if not api_key:
        api_key = existing_env.get(provider_config.api_key_env, "").strip()

    model = _prompt_text(
        f"Model name for {provider_config.label}",
        default=default_model,
    )
    base_url = None
    if provider_config.base_url_env:
        base_url = _prompt_text(
            f"Custom API base URL for {provider_config.label} (optional)",
            default=existing_env.get(provider_config.base_url_env, ""),
            allow_blank=True,
        )

    env_values = build_env_values(
        selected_provider=selected_provider,
        api_key=api_key,
        existing_env=existing_env,
        model=model,
        base_url=base_url,
    )

    validation_errors = validate_runtime_env(env_values)
    if validation_errors:
        print("\nThe setup is missing a few required values:")
        for error in validation_errors:
            print(f"  - {error}")
        print("\nRun the wizard again once you have a valid provider key.")
        return 1

    print("\nPreparing the local Python environment...")
    _ensure_virtualenv()
    _install_dependencies()

    ENV_PATH.write_text(render_env_file(env_values), encoding="utf-8")

    print("\nSetup complete.")
    print(f"- Provider: {provider_config.label}")
    print(f"- Model: {env_values['LLM_MODEL']}")
    print(f"- Config file: {ENV_PATH}")
    print("- App URL: http://127.0.0.1:8000/")

    if _prompt_yes_no("\nStart the web app now?", default=True):
        return _run_local_app()

    print("\nYou can launch it later with:")
    if sys.platform == "win32":
        print("  start.bat")
    else:
        print("  ./start.command")
    print("You can also run: python3 scripts/run_local.py")
    return 0


def _ensure_virtualenv() -> None:
    venv_path = PROJECT_ROOT / ".venv"
    if venv_path.exists():
        return

    print("- Creating .venv")
    _run_command([sys.executable, "-m", "venv", str(venv_path)])


def _install_dependencies() -> None:
    python_bin = venv_python_path(PROJECT_ROOT)
    if not python_bin.exists():
        raise SystemExit(
            "The virtual environment was created, but its Python executable was not found."
        )

    print("- Installing Python build tools")
    _run_command(
        [str(python_bin), "-m", "pip", "install", "setuptools>=68"],
        failure_hint=(
            "The setup wizard needs internet access the first time it installs Python packages."
        ),
    )

    print("- Installing project dependencies")
    _run_command(
        [str(python_bin), "-m", "pip", "install", "."],
        failure_hint=(
            "The setup wizard could not install project dependencies. "
            "Please check your internet connection and try again."
        ),
    )


def _run_local_app() -> int:
    return subprocess.call(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "run_local.py")],
        cwd=PROJECT_ROOT,
    )


def _run_command(command: list[str], *, failure_hint: str | None = None) -> None:
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if completed.returncode != 0:
        if failure_hint:
            print(f"\n{failure_hint}")
        raise SystemExit(completed.returncode)


def _prompt_provider(current_value: str | None) -> str:
    options = {
        "1": "openai",
        "2": "anthropic",
        "3": "gemini",
    }
    default_provider = current_value or "openai"
    default_choice = next(
        (choice for choice, provider in options.items() if provider == default_provider),
        "1",
    )

    print("Choose your model provider:")
    print("  1. OpenAI")
    print("  2. Anthropic Claude")
    print("  3. Google Gemini")

    while True:
        choice = input(f"Provider [{default_choice}]: ").strip() or default_choice
        if choice in options:
            return options[choice]
        print("Please enter 1, 2, or 3.")


def _prompt_text(prompt: str, *, default: str = "", allow_blank: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if allow_blank:
            return ""
        print("This value is required.")


def _prompt_yes_no(prompt: str, *, default: bool) -> bool:
    default_hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_hint}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def _mask_secret(value: str) -> str:
    stripped = value.strip()
    if len(stripped) < 8:
        return ""
    return f"{stripped[:4]}...{stripped[-4:]}"


if __name__ == "__main__":
    raise SystemExit(main())
