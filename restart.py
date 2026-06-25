#!/usr/bin/env python3
"""TradeDoctor dev restart script — cross-platform (Windows / Linux).

Usage: python restart.py

Prerequisites (both platforms):
    - Python 3.10+ with backend/.venv
    - Node.js 18+ (npx available in PATH)
    - PostgreSQL (or SQLite for dev)
"""

import os
import sys
import time
import signal
import socket
import platform
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
LOG_DIR = ROOT / ".tmp"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

IS_WINDOWS = platform.system() == "Windows"
PYTHON = (
    BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    if IS_WINDOWS
    else BACKEND_DIR / ".venv" / "bin" / "python"
)

LOG_DIR.mkdir(parents=True, exist_ok=True)


def ok(msg: str) -> None:
    print(f"  [ok] {msg}")


def fail(msg: str) -> None:
    print(f"  [fail] {msg}")


# ── Step 1: Free ports ──────────────────────────────────────────────

def _pid_listening(port: int) -> str | None:
    """Return PID (as string) of process listening on `port`, or None."""
    if IS_WINDOWS:
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, timeout=5
            )
            for line in out.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    return line.strip().split()[-1]
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f":{port}"], text=True, timeout=5
            )
            return out.strip() or None
        except Exception:
            pass
    return None


def _kill_pid(pid: str) -> bool:
    """Kill a process by PID. Returns True on success."""
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/PID", pid],
                capture_output=True, timeout=5,
            )
        else:
            os.kill(int(pid), signal.SIGKILL)
        return True
    except Exception:
        return False


def free_ports() -> None:
    print(f"[1/3] Freeing ports {BACKEND_PORT} {FRONTEND_PORT} ...")
    for port in (BACKEND_PORT, FRONTEND_PORT):
        pid = _pid_listening(port)
        if pid and _kill_pid(pid):
            print(f"  :{port} PID={pid} killed")
    print("  done")
    time.sleep(0.5)


# ── Step 2 & 3: Start servers ────────────────────────────────────────

def _detach_popen(cmd: list[str], log_path: Path, cwd: Path) -> subprocess.Popen:
    """Start a process detached from the terminal, output → log file."""
    log_fh = open(log_path, "w", encoding="utf-8", errors="replace")
    kwargs: dict = dict(
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=str(cwd),
        close_fds=True,
    )
    if IS_WINDOWS:
        # CREATE_NEW_PROCESS_GROUP + no console window
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def start_backend() -> int:
    print(f"[2/3] Starting backend :{BACKEND_PORT} ...")
    cmd = [
        str(PYTHON), "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", str(BACKEND_PORT),
    ]
    proc = _detach_popen(cmd, LOG_DIR / "backend.log", BACKEND_DIR)
    ok(f"PID={proc.pid}  log: {LOG_DIR / 'backend.log'}")
    return proc.pid


def start_frontend() -> int:
    print(f"[3/3] Starting frontend :{FRONTEND_PORT} ...")
    if IS_WINDOWS:
        cmd = ["cmd.exe", "/c", "npx", "vite", "--port", str(FRONTEND_PORT)]
    else:
        cmd = ["npx", "vite", "--port", str(FRONTEND_PORT)]
    proc = _detach_popen(cmd, LOG_DIR / "frontend.log", FRONTEND_DIR)
    ok(f"PID={proc.pid}  log: {LOG_DIR / 'frontend.log'}")
    return proc.pid


# ── Step 4: Health check ─────────────────────────────────────────────

def wait_backend(timeout: float = 15.0) -> bool:
    print()
    print("  Waiting for backend", end="", flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(
                f"http://localhost:{BACKEND_PORT}/api/health"
            )
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    print()
                    ok("Backend ready")
                    return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(0.5)
    print()
    fail(f"Backend did not start within {timeout:.0f}s, check log: {LOG_DIR / 'backend.log'}")
    return False


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Restarting TradeDoctor (dev) ===")

    free_ports()
    start_backend()
    start_frontend()

    if not wait_backend():
        sys.exit(1)

    print()
    print(f"  http://localhost:{FRONTEND_PORT}  <- Frontend")
    print(f"  http://localhost:{BACKEND_PORT}/api/health  <- Backend health")
    print(f"  Logs: {LOG_DIR}")
    print("=== Done ===")


if __name__ == "__main__":
    main()
