#!/usr/bin/env python3
"""AI Telecalling SaaS - Unified Local Development Runner.

Runs both Backend (FastAPI via uvicorn) and Frontend (Next.js via npm) concurrently.
Handles graceful shutdown of all child processes on Ctrl+C.

Usage:
    python run.py              # Run both unified in the current console
    python run.py --separate   # Launch backend and frontend in separate windows
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
VENV_DIR = ROOT_DIR / ".venv"

# Windows virtualenv python vs system python
if sys.platform == "win32":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"

PYTHON_BIN = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Enable ANSI colors in Windows CMD if needed
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def stream_logs(pipe, prefix: str, color: str):
    """Stream stdout/stderr line by line with a colored prefix."""
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            clean_line = line.rstrip("\r\n")
            print(f"{color}{prefix}{RESET} {clean_line}", flush=True)
    except (ValueError, OSError):
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def kill_process_tree(pid: int):
    """Forcefully kill a process and all its children."""
    if not pid:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass


def preflight_checks():
    """Verify environment setup before starting servers."""
    print(f"{BOLD}=== AI Telecalling SaaS Local Runner ==={RESET}")

    # Check .env
    backend_env = ROOT_DIR / "backend" / ".env"
    example_env = ROOT_DIR / ".env.example"
    if not backend_env.exists():
        if example_env.exists():
            print(f"{YELLOW}[SETUP]{RESET} backend/.env not found. Creating from .env.example...")
            try:
                import shutil
                shutil.copy(example_env, backend_env)
                print(f"{GREEN}[SETUP]{RESET} Created backend/.env successfully.")
            except Exception as e:
                print(f"{RED}[ERROR]{RESET} Failed to create backend/.env: {e}")
        else:
            print(f"{YELLOW}[WARNING]{RESET} backend/.env not found and no .env.example found.")
    else:
        print(f"{GREEN}[OK]{RESET} backend/.env found.")

    # Check venv
    if VENV_PYTHON.exists():
        print(f"{GREEN}[OK]{RESET} Virtual environment detected ({VENV_PYTHON})")
    else:
        print(f"{YELLOW}[NOTE]{RESET} .venv not found. Using system Python: {PYTHON_BIN}")

    # Check frontend node_modules
    if not (FRONTEND_DIR / "node_modules").exists():
        print(f"{YELLOW}[WARNING]{RESET} frontend/node_modules not found. Run 'cd frontend && npm install' if startup fails.")
    else:
        print(f"{GREEN}[OK]{RESET} frontend/node_modules found.")

    # Port checks
    if is_port_in_use(8000):
        print(f"{YELLOW}[WARNING]{RESET} Port 8000 is already in use! Another backend instance may still be running.")
    if is_port_in_use(3000):
        print(f"{YELLOW}[WARNING]{RESET} Port 3000 is already in use! Another frontend instance may still be running.")

    print(f"\n{BOLD}Starting services:{RESET}")
    print(f"  - {CYAN}Backend:{RESET}  http://localhost:8000  (Docs: http://localhost:8000/docs)")
    print(f"  - {GREEN}Frontend:{RESET} http://localhost:3000")
    print(f"Press {BOLD}Ctrl+C{RESET} to stop both services cleanly.\n")


def run_separate():
    """Launch backend and frontend in separate console windows (Windows)."""
    preflight_checks()
    if sys.platform != "win32":
        print(f"{RED}[ERROR]{RESET} --separate mode is only supported on Windows.")
        sys.exit(1)

    backend_cmd = (
        f'cd /d "{ROOT_DIR}" && '
        f'if exist .venv\\Scripts\\activate.bat (call .venv\\Scripts\\activate.bat) && '
        f'python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload'
    )
    frontend_cmd = f'cd /d "{FRONTEND_DIR}" && npm run dev'

    print(f"{CYAN}Opening Backend window...{RESET}")
    subprocess.Popen(f'start "AI Telecalling - Backend (Port 8000)" cmd /k "{backend_cmd}"', shell=True)

    print(f"{GREEN}Opening Frontend window...{RESET}")
    subprocess.Popen(f'start "AI Telecalling - Frontend (Port 3000)" cmd /k "{frontend_cmd}"', shell=True)

    print(f"\n{GREEN}[DONE]{RESET} Backend and Frontend launched in separate windows.")


def run_unified():
    """Run both services unified in the current console with log prefixing."""
    preflight_checks()

    # Commands
    backend_args = [
        PYTHON_BIN,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ]

    # npm executable resolution
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_args = [npm_cmd, "run", "dev"]

    backend_proc = None
    frontend_proc = None

    try:
        # Start Backend
        backend_proc = subprocess.Popen(
            backend_args,
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        # Start Frontend
        frontend_proc = subprocess.Popen(
            frontend_args,
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        # Threaded readers
        backend_thread = threading.Thread(
            target=stream_logs,
            args=(backend_proc.stdout, "[BACKEND] ", CYAN),
            daemon=True,
        )
        frontend_thread = threading.Thread(
            target=stream_logs,
            args=(frontend_proc.stdout, "[FRONTEND]", GREEN),
            daemon=True,
        )

        backend_thread.start()
        frontend_thread.start()

        # Wait for either process to terminate
        while True:
            if backend_proc.poll() is not None:
                print(f"\n{RED}[BACKEND] Process exited with code {backend_proc.returncode}{RESET}")
                break
            if frontend_proc.poll() is not None:
                print(f"\n{RED}[FRONTEND] Process exited with code {frontend_proc.returncode}{RESET}")
                break
            threading.Event().wait(0.5)

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[SHUTDOWN] Interrupted by user. Stopping servers...{RESET}")
    finally:
        if backend_proc and backend_proc.poll() is None:
            print(f"{CYAN}[SHUTDOWN] Stopping Backend (PID {backend_proc.pid})...{RESET}")
            kill_process_tree(backend_proc.pid)
        if frontend_proc and frontend_proc.poll() is None:
            print(f"{GREEN}[SHUTDOWN] Stopping Frontend (PID {frontend_proc.pid})...{RESET}")
            kill_process_tree(frontend_proc.pid)

        print(f"{BOLD}[SHUTDOWN] All services stopped cleanly.{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Run AI Telecalling Backend & Frontend together.")
    parser.add_argument(
        "--separate",
        "-s",
        action="store_true",
        help="Open Backend and Frontend in separate console windows (Windows only)",
    )
    args = parser.parse_args()

    if args.separate:
        run_separate()
    else:
        run_unified()


if __name__ == "__main__":
    main()
