"""
Full user flow E2E tests using Playwright.
Covers: register → login → upload CSV → confirm format → import → dashboard (all 3 tabs) → report.

Usage:
    # With both servers already running:
    python e2e/user_flow_e2e.py

    # With auto server management:
    python scripts/with_server.py \
      --server "cd backend && .venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000" --port 8000 \
      --server "cd frontend && npx vite --host 0.0.0.0 --port 5173" --port 5173 \
      -- python e2e/user_flow_e2e.py
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright, Page

FRONTEND = "http://localhost:5173"
BACKEND = "http://localhost:8000"

CSV_CONTENT = (
    "委托时间,证券代码,买卖方向,成交价格,成交数量,成交金额\n"
    "2026-01-05 09:35:00,600519,买入,1500.00,100,150000\n"
    "2026-01-06 09:30:00,000858,买入,120.00,200,24000\n"
    "2026-01-10 14:20:00,600519,卖出,1520.00,100,152000\n"
    "2026-01-12 10:15:00,000858,卖出,125.00,200,25000\n"
    "2026-01-15 13:00:00,601318,买入,80.00,500,40000\n"
    "2026-01-20 10:30:00,601318,卖出,78.00,500,39000\n"
)

PASS = 0
FAIL = 0


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def run():
    global PASS, FAIL
    print("=" * 60)
    print("TradingJournalAnalyzer E2E User Flow Test")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # ─── Landing Page ───────────────────────────────
            print("\n── 1. Landing Page ──")
            page.goto(FRONTEND, wait_until="networkidle")
            check("TradingJournalAnalyzer" in page.title() or page.locator("nav").is_visible(),
                  "landing page loads with nav")

            # ─── Register ────────────────────────────────────
            print("\n── 2. Register ──")
            page.click("text=注册")
            page.wait_for_url("**/register")
            page.fill('input[name="email"], input[type="email"], input[placeholder*="邮箱"]', f"e2e_{int(time.time())}@test.com")
            page.fill('input[type="password"]', "e2etest123")
            page.click('button:has-text("注册")')
            page.wait_for_url("**/upload", timeout=10000)
            check("/upload" in page.url, f"redirected to upload after register: {page.url}")

            # Navigation shows logged-in state
            check(page.locator("nav >> text=上传").is_visible(), "nav shows 上传 link")
            check(page.locator("nav >> text=退出").is_visible(), "nav shows 退出 button")

            # ─── Upload CSV ──────────────────────────────────
            print("\n── 3. Upload CSV ──")
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
                f.write(CSV_CONTENT)
                csv_path = f.name

            # Click dropzone to trigger file chooser, then upload
            with page.expect_file_chooser() as fc_info:
                page.locator("text=拖拽交割单").click()
            fc_info.value.set_files(csv_path)
            page.wait_for_timeout(2000)

            # ─── Format Detection ────────────────────────────
            print("\n── 4. Format Detection ──")
            check(page.locator("text=自动识别").is_visible() or page.locator("text=确认格式").is_visible(),
                  "format auto-detected or selector shown")
            check(not page.locator("text=NaN%").is_visible(), "no NaN% displayed")

            # ─── Confirm Format ──────────────────────────────
            print("\n── 5. Confirm Format ──")
            confirm_btn = page.locator("button:has-text('确认格式')")
            if confirm_btn.is_visible():
                confirm_btn.click()
            else:
                # Manual selection fallback
                page.locator("button").first.click()
            page.wait_for_timeout(2000)

            # ─── Preview ─────────────────────────────────────
            print("\n── 6. Preview ──")
            check(page.locator("text=确认导入").is_visible(), "import button visible after confirm")
            check(page.locator("table").is_visible(), "preview table visible")

            # ─── Import ──────────────────────────────────────
            print("\n── 7. Import ──")
            page.click("button:has-text('确认导入')")
            page.wait_for_url("**/analysis/**", timeout=15000)
            check("/analysis/" in page.url, f"redirected to analysis after import: {page.url}")

            # ─── Dashboard: Stats Tab ────────────────────────
            print("\n── 8. Dashboard - Stats ──")
            page.wait_for_timeout(3000)
            check(page.locator("text=统计概览").is_visible(), "stats tab visible")
            check(not page.locator("text=6667%").is_visible() and not page.locator("text=NaN%").is_visible(),
                  "no corrupted percentage values")
            # Verify key KPI cards
            check(page.locator("text=胜率").is_visible(), "win rate card visible")
            check(page.locator("text=总盈亏").is_visible(), "total pnl card visible")

            # ─── Dashboard: Insight Tab ──────────────────────
            print("\n── 9. Dashboard - Insight ──")
            page.click("button:has-text('归因分析')")
            page.wait_for_timeout(2000)
            # Should show formatted table, not raw JSON
            check(not page.locator("text=pattern_name").is_visible(),
                  "insight tab shows formatted data (no raw JSON field names)")
            check(page.locator("table").is_visible(), "pattern table visible")

            # ─── Dashboard: What If Tab ──────────────────────
            print("\n── 10. Dashboard - What If ──")
            page.click("button:has-text('What If')")
            page.wait_for_timeout(2000)
            check(page.locator("text=伤害指数").first.is_visible() or page.locator("text=原始").first.is_visible(),
                  "what if results visible")

            # ─── Navigation ──────────────────────────────────
            print("\n── 11. Navigation ──")
            page.locator("nav >> text=历史").click()
            page.wait_for_url("**/history")
            check("/history" in page.url, "navigated to history page")

            page.locator("nav >> text=上传").click()
            page.wait_for_url("**/upload")
            check("/upload" in page.url, "navigated back to upload page")

            # ─── Logout ──────────────────────────────────────
            print("\n── 12. Logout ──")
            page.locator("nav >> text=退出").click()
            page.wait_for_timeout(1000)
            check(page.locator("nav >> text=登录").is_visible(), "login link visible after logout")

            # Cleanup temp CSV
            os.unlink(csv_path)

        except Exception as e:
            print(f"\n  [FATAL] EXCEPTION: {e}")
            page.screenshot(path="e2e_failure.png", full_page=True)
            print("  Screenshot saved to e2e_failure.png")
            FAIL += 1

        finally:
            browser.close()

    # ─── Summary ─────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"E2E Results: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
    print(f"{'='*60}")
    return FAIL == 0


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
