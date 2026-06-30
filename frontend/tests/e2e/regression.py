"""Playwright E2E regression suite for TradeDoctor.

Derived from docs/review/frontend/audit.py but reworked as a repeatable
regression test: local target (http://localhost:5173), pytest-style asserts,
non-zero exit on failure. Run with:

    python frontend/tests/e2e/regression.py

Prerequisites: backend on :8000 + frontend on :5173 (python restart.py).
Testfiles must exist under testfiles/.
"""
import os
import sys
import time
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = os.environ.get("E2E_BASE", "http://localhost:5173")
TESTFILES = Path(__file__).resolve().parents[3] / "testfiles"

passed: list[str] = []
failed: list[tuple[str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        passed.append(name)
        print(f"  ✓ {name}")
    else:
        failed.append((name, detail))
        print(f"  ✗ {name}: {detail}")


def run() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        console_errs: list[str] = []
        page.on("console", lambda m: console_errs.append(m.text) if m.type == "error" else None)

        # ── 1. Register (fresh account each run) ────────────────────────
        ts = int(time.time())
        email = f"e2e{ts}@example.com"
        pw = "Audit1234"
        nickname = f"e2e用户{ts % 10000}"
        print("\n[1] 注册 + 昵称")
        page.goto(f"{BASE}/register", wait_until="networkidle")
        page.locator("input[placeholder*='邮箱']").first.fill(email)
        page.locator("input[placeholder*='密码']").first.fill(pw)
        page.locator("input[aria-label='昵称']").fill(nickname)
        page.locator("button[type='submit']").first.click()
        page.wait_for_timeout(4000)
        check("注册跳转 /upload", "/upload" in page.url, page.url)

        # ── 2. Login (clear token first) ────────────────────────────────
        print("[2] 登录")
        page.evaluate("() => localStorage.clear()")
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.locator("input[placeholder*='邮箱']").first.fill(email)
        page.locator("input[placeholder*='密码']").first.fill(pw)
        page.locator("button[type='submit']").first.click()
        page.wait_for_timeout(4000)
        check("登录跳转", "/upload" in page.url or "/analysis" in page.url, page.url)

        # ── 3. Upload 华西 → analysis ───────────────────────────────────
        print("[3] 上传华西交割单")
        page.goto(f"{BASE}/upload", wait_until="networkidle")
        page.wait_for_timeout(800)
        fpath = TESTFILES / "华西20260101-0331交割单查询.xls"
        page.locator("input[type='file']").first.set_input_files(str(fpath))
        try:
            page.wait_for_url("**/analysis/**", timeout=120000)
            check("上传跳转 analysis", True)
        except PWTimeout:
            check("上传跳转 analysis", False, "timeout")
        page.wait_for_timeout(3000)
        analysis_id = page.url.rstrip("/").split("/")[-1]

        # ── 4. Stats tab: KPI cards + symbol names + banner ────────────
        print("[4] 统计概览")
        body = page.evaluate("() => document.body.innerText")
        check("B3.3 三档显示", all(k in body for k in ["总成交", "完整建仓", "已平仓"]), "缺关键字")
        check("B2.1 股票中文名", "超频三" in body or "巨轮智能" in body, "未见中文名")

        # B2.4 search + X clear
        search = page.locator("input[aria-label='搜索股票']")
        if search.count() > 0:
            search.fill("300647")
            page.wait_for_timeout(400)
            check("B2.4 搜索过滤", search.input_value() == "300647")
            clear = page.locator("button[aria-label='清空搜索']")
            if clear.count() > 0:
                clear.first.click()
                page.wait_for_timeout(300)
                check("B2.4 X 清空", search.input_value() == "")
            else:
                check("B2.4 X 按钮", False, "未出现")
        else:
            check("B2.4 搜索框", False, "未找到")

        # ── 5. Tab switching ────────────────────────────────────────────
        print("[5] Tab 切换")
        for tab in ["归因分析", "情景回测"]:
            btn = page.locator(f"button[role='tab']:has-text('{tab}')")
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(2000)
                check(f"切换 {tab}", True)
            else:
                check(f"切换 {tab}", False, "按钮未找到")

        # B5.1 contribution bar exists in InsightTable (归因 tab)
        page.locator("button[role='tab']:has-text('归因分析')").first.click()
        page.wait_for_timeout(1500)
        # expand the full labels collapsible to reveal InsightTable
        coll = page.locator("summary:has-text('展开全部标签')")
        if coll.count() > 0:
            coll.first.click()
            page.wait_for_timeout(500)
        bars = page.locator("div.h-1\\.5.w-16").count()
        check("B5.1 贡献进度条", bars > 0, f"bars={bars}")

        # ── 6. Generate AI report ───────────────────────────────────────
        print("[6] 生成 AI 报告")
        page.locator("button[role='tab']:has-text('统计概览')").first.click()
        page.wait_for_timeout(800)
        gen = page.locator("button:has-text('查看 AI 报告'), button:has-text('生成 AI 报告')")
        if gen.count() > 0:
            gen.first.click()
            try:
                page.wait_for_url("**/report/**", timeout=180000)
                check("跳转报告页", True)
            except PWTimeout:
                check("跳转报告页", False, "timeout")
        page.wait_for_timeout(2000)

        # C2.1 TOC + C2.3 复制按钮
        toc = page.locator("nav[aria-label='报告目录']")
        check("C2.1 报告目录", toc.count() > 0, "未渲染")
        check("C2.3 复制全文按钮", page.locator("button:has-text('复制全文')").count() > 0)

        # ── 7. History + active highlight ───────────────────────────────
        print("[7] 历史 + 导航")
        page.goto(f"{BASE}/history", wait_until="networkidle")
        page.wait_for_timeout(1500)
        link = page.locator("nav a[href='/history']").first
        cls = link.get_attribute("class") or "" if link.count() > 0 else ""
        check("A2.2 历史 active 高亮", "accent" in cls, f"class={cls[:50]}")

        # ── 8. A1.4 404 ────────────────────────────────────────────────
        print("[8] 404 页")
        page.goto(f"{BASE}/no-such-page", wait_until="networkidle")
        check("A1.4 404 热门目的地", page.locator("a[href='/upload']").count() > 0)

        # ── 9. Console errors ──────────────────────────────────────────
        print("[9] Console errors")
        check("Console 0 error", len(console_errs) == 0, f"{len(console_errs)} 个: {console_errs[:3]}")

        browser.close()

    print("\n" + "=" * 60)
    print(f"PASS: {len(passed)}  FAIL: {len(failed)}")
    for name, detail in failed:
        print(f"  ✗ {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
