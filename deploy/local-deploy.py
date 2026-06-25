#!/usr/bin/env python3
"""
TradeDoctor — 本地构建 + rsync 全量代码部署

用法：
  python deploy/local-deploy.py                 # 完整流程
  python deploy/local-deploy.py --skip-build    # 跳过 npm build
  python deploy/local-deploy.py --dry-run       # 只显示 rsync 影响不实际执行
  python deploy/local-deploy.py --no-venv       # 跳过 Python venv 检测

工作流程：
  1. 本地构建前端 → 2. rsync 整个项目（含源码+dist）到服务器
  → 3. SSH 触发服务器端更新（pip install + 备份 + alembic + 重启 + 健康检查）
"""

import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path


# ============ 配置区 ============
SERVER_USER = "root"
SERVER_HOST = "47.109.159.232"
PROJECT_PATH = "/opt/TradeDoctor"

RSYNC_EXCLUDES = [
    ".git",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "frontend/node_modules",
    "backend/.venv",
    "backend/venv",
    "backend/uploads",
    ".env",
    ".claude",
]
# ================================

# ANSI 颜色
G = "\033[0;32m"
Y = "\033[0;33m"
R = "\033[0;31m"
B = "\033[0;34m"
N = "\033[0m"


def log(msg: str) -> None:
    print(f"{G}[deploy]{N} {msg}")


def warn(msg: str) -> None:
    print(f"{Y}[warn]{N} {msg}")


def error(msg: str) -> None:
    print(f"{R}[error]{N} {msg}")


def step(num: str, msg: str) -> None:
    print(f"{B}[{num}]{N} {msg}")


def run(cmd: list[str], cwd: str | None = None, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """运行命令，失败时退出。Windows 上通过 shell 执行以解析 .cmd/.ps1 等。"""
    cmd_str = shlex.join(cmd)
    log(f"  $ {cmd_str}")
    result = subprocess.run(
        cmd_str if sys.platform == "win32" else cmd,
        cwd=cwd, check=False, capture_output=capture, text=True,
        shell=(sys.platform == "win32"),
    )
    if check and result.returncode != 0:
        error(f"命令失败 (exit={result.returncode}): {cmd_str}")
        if capture and result.stderr:
            error(result.stderr.strip())
        sys.exit(1)
    return result


def has_venv(dir_path: Path) -> bool:
    """检测目录下是否存在 Python 虚拟环境。"""
    return (dir_path / ".venv").is_dir() or (dir_path / "venv").is_dir()


def main() -> None:
    parser = argparse.ArgumentParser(description="TradeDoctor 本地构建 + rsync 部署")
    parser.add_argument("--skip-build", action="store_true", help="跳过 npm build")
    parser.add_argument("--dry-run", action="store_true", help="仅列出 rsync 影响，不实际执行")
    parser.add_argument("--no-venv", action="store_true", help="跳过 Python 虚拟环境检测")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    start_time = time.monotonic()

    # ---- 0. 环境检测 ----
    if not args.no_venv and has_venv(project_dir / "backend"):
        log("检测到后端虚拟环境（venv），且未传 --no-venv，假设本地开发环境正确，跳过额外检测")

    # ---- 1. 本地构建前端 ----
    if not args.skip_build:
        step("1/3", "本地构建前端...")
        frontend_dir = project_dir / "frontend"
        if not (frontend_dir / "node_modules").is_dir():
            log("安装 npm 依赖...")
            run(["npm", "install"], cwd=str(frontend_dir))
        log("VITE_API_BASE 不设置，前端走相对路径，依赖 nginx /api 反代")
        run(["npm", "run", "build"], cwd=str(frontend_dir))
        log("前端构建完成: frontend/dist/")
    else:
        step("1/3", "跳过前端构建（使用已有 dist/）")
    print()

    # ---- 2. rsync 整个项目到服务器 ----
    step("2/3", "同步代码到服务器...")
    ssh_target = f"{SERVER_USER}@{SERVER_HOST}:{PROJECT_PATH}/"

    excludes: list[str] = []
    for pattern in RSYNC_EXCLUDES:
        excludes.extend(["--exclude", pattern])

    if args.dry_run:
        log("DRY RUN — 仅列出会被同步的文件：")
        result = subprocess.run(
            ["rsync", "-avz", "--delete", "--dry-run", *excludes,
             f"{project_dir}/", ssh_target],
            capture_output=True, text=True,
        )
        lines = [l for l in result.stdout.splitlines() if not l.endswith("/")]
        for line in lines[:50]:
            print(f"    {line}")
        if len(lines) > 50:
            print("    ...")
        log("DRY RUN 完成，未实际传输")
        return

    run(["rsync", "-avz", "--delete", *excludes, f"{project_dir}/", ssh_target])
    log("代码同步完成")

    # 检查服务器端 update.sh 是否存在
    check_result = subprocess.run(
        ["ssh", f"{SERVER_USER}@{SERVER_HOST}",
         f"test -f {PROJECT_PATH}/deploy/update.sh"],
        check=False,
    )
    if check_result.returncode != 0:
        error(f"服务器上找不到 {PROJECT_PATH}/deploy/update.sh！")
        print("  请先手动在服务器上创建项目目录并上传初始代码")
        sys.exit(1)
    log("服务器端 update.sh 存在")
    print()

    # ---- 3. SSH 触发服务器端更新 ----
    step("3/3", "触发服务器端更新...")
    run(["ssh", f"{SERVER_USER}@{SERVER_HOST}",
         f"bash {PROJECT_PATH}/deploy/update.sh"])

    elapsed = time.monotonic() - start_time
    print()
    log(f"部署完成！耗时 {elapsed:.0f}s")
    log(f"  前端构建: {'跳过' if args.skip_build else '已构建'}")
    log("  代码同步: rsync 全量（排除 node_modules/.venv/uploads/.env/.git）")
    log("  服务端:   pip install + 备份 + alembic + 重启 + 健康检查")


if __name__ == "__main__":
    main()
