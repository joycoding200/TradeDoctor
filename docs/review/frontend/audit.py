"""
TradingJournalAnalyzer 前端全面审查 v3
修复:
  - 使用 press_sequentially 触发 React 受控 onChange
  - 邮箱用合法 .com 域避免 HTML5 拦截
  - 等待 networkidle 后再操作
  - 添加错误截图与详情
"""
import os
import sys
import time
import json
import traceback
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "http://47.109.159.232"
OUTPUT_DIR = "D:/Dev/Projects/TradingJournalAnalyzer/.tmp/audit"
TESTFILES_DIR = "D:/Dev/Projects/TradingJournalAnalyzer/testfiles"

os.makedirs(OUTPUT_DIR, exist_ok=True)

REPORT = {
    "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "base_url": BASE_URL,
    "pages": [],
    "console_errors": [],
    "network_failures": [],
    "uploads": [],
    "issues": [],
    "ux_observations": [],
    "ai_diagnostics": [],
}


def on_console(msg):
    try:
        if msg.type == "error":
            text = msg.text
            if "favicon" in text.lower():
                return
            REPORT["console_errors"].append({"type": msg.type, "text": text[:500]})
    except Exception:
        pass


def on_response(resp):
    try:
        if resp.status >= 400:
            REPORT["network_failures"].append(
                {"url": resp.url, "status": resp.status, "method": resp.request.method}
            )
    except Exception:
        pass


def shot(page, name):
    path = os.path.join(OUTPUT_DIR, name + ".png")
    try:
        page.screenshot(path=path, full_page=True)
        print(f"  [shot] {name}")
    except Exception as e:
        print(f"  [shot-fail] {name}: {e}")


def visit(page, name, url, wait_for=None, timeout=30000):
    print(f"\n=== {name} -> {url} ===")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            REPORT["issues"].append(f"{name}: networkidle 等待超时")
    except PlaywrightTimeout:
        REPORT["issues"].append(f"{name}: 页面加载超时")
    if wait_for:
        try:
            page.wait_for_selector(wait_for, timeout=10000)
        except PlaywrightTimeout:
            REPORT["issues"].append(f"{name}: 选择器 '{wait_for}' 未出现")
    page.wait_for_timeout(1500)
    shot(page, name)
    REPORT["pages"].append(
        {"name": name, "url": page.url, "title": page.title() if page.title() else ""}
    )


def fill_input(page, placeholder_substr, value):
    """通过 placeholder 定位并 press_sequentially 以触发受控 onChange"""
    loc = page.locator(f"input[placeholder*='{placeholder_substr}']").first
    loc.click()
    loc.clear()
    loc.press_sequentially(value, delay=20)
    page.wait_for_timeout(300)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
            locale="zh-CN",
        )
        page = context.new_page()
        page.on("console", on_console)
        page.on("response", on_response)

        # 1. Landing 未登录
        visit(page, "01_landing", f"{BASE_URL}/")
        if page.locator("text=邮箱注册").count() > 0:
            REPORT["ux_observations"].append(
                "Landing: 未登录显示内嵌登录/注册切换 (AuthTabs)"
            )

        # 2. Register
        ts = int(time.time())
        email = f"audit{ts}@example.com"
        password = "Audit1234"
        visit(page, "02_register", f"{BASE_URL}/register", wait_for="input[placeholder*='邮箱']")
        try:
            fill_input(page, "邮箱", email)
            fill_input(page, "密码", password)
            # 提交
            page.locator("button[type='submit']").first.click()
            page.wait_for_timeout(5000)
            shot(page, "02b_register_after")
            print(f"  [register] url after submit: {page.url}")
            if "/upload" in page.url:
                REPORT["ux_observations"].append("register: 提交后跳转 /upload ✓")
            elif "/register" in page.url:
                # 看看错误
                err = page.locator(".text-danger").all_text_contents()
                REPORT["issues"].append(f"register: 未跳转，仍在 /register，错误提示: {err}")
            else:
                REPORT["ux_observations"].append(f"register: 跳转到 {page.url}")
        except Exception as e:
            REPORT["issues"].append(f"register: {e}")
            shot(page, "02_register_err")

        # 3. Login
        # 先清掉 token 然后访问 login
        try:
            page.evaluate("() => localStorage.clear()")
        except Exception:
            pass
        visit(page, "03_login", f"{BASE_URL}/login", wait_for="input[placeholder*='邮箱或手机号']")
        try:
            fill_input(page, "邮箱或手机号", email)
            fill_input(page, "密码", password)
            page.locator("button[type='submit']").first.click()
            page.wait_for_timeout(5000)
            shot(page, "03b_login_after")
            print(f"  [login] url after submit: {page.url}")
            if "/upload" in page.url or "/analysis" in page.url:
                REPORT["ux_observations"].append("login: 提交后跳转 ✓")
            else:
                err = page.locator(".text-danger").all_text_contents()
                REPORT["issues"].append(f"login: 未跳转，错误: {err}")
        except Exception as e:
            REPORT["issues"].append(f"login: {e}")
            shot(page, "03_login_err")

        # 4. Upload
        visit(page, "04_upload", f"{BASE_URL}/upload")
        # 应该跳到 upload（如果登录成功）

        # 5. 上传 .xls 文件
        test_files = [
            "华西20260101-0331交割单查询.xls",
            "中信20260101-0331交割单.xls",
            "天风2026-1月.xls",
        ]
        uploaded_analysis_ids = []

        for fname in test_files:
            fpath = os.path.join(TESTFILES_DIR, fname)
            if not os.path.exists(fpath):
                REPORT["issues"].append(f"file missing: {fpath}")
                continue
            print(f"\n=== Upload: {fname} ===")
            try:
                page.goto(f"{BASE_URL}/upload", wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeout:
                    pass
                page.wait_for_timeout(1500)
                # file input 即使 hidden 也可 set_input_files
                fi = page.locator("input[type='file']")
                if fi.count() == 0:
                    REPORT["issues"].append(f"upload({fname}): no file input")
                    continue
                fi.first.set_input_files(fpath)
                # 等待 60s 内跳转到 /analysis/...
                try:
                    page.wait_for_url("**/analysis/**", timeout=120000)
                    REPORT["ux_observations"].append(
                        f"upload({fname}): 自动跳转到 {page.url}"
                    )
                    shot(page, f"05_upload_{fname.replace('.', '_')}")
                    m = page.url.rstrip("/").split("/")
                    if "analysis" in m:
                        idx = m.index("analysis")
                        if idx + 1 < len(m):
                            uploaded_analysis_ids.append(m[idx + 1])
                except PlaywrightTimeout:
                    shot(page, f"05_upload_{fname.replace('.', '_')}_nojump")
                    body = page.evaluate("() => document.body.innerText")
                    REPORT["uploads"].append(
                        {"file": fname, "url": page.url, "snippet": body[:800]}
                    )
                    # 检查 toast
                    toasts = page.locator("[role='alert'], .text-danger, .toast").all_text_contents()
                    if toasts:
                        REPORT["issues"].append(
                            f"upload({fname}) toast/alert: {toasts[:3]}"
                        )
            except Exception as e:
                REPORT["issues"].append(f"upload({fname}): {e}")
                shot(page, f"05_upload_err_{fname.replace('.', '_')}")

        # 6. Analysis（取最后一个成功的）
        if uploaded_analysis_ids:
            aid = uploaded_analysis_ids[-1]
            visit(page, "06_analysis", f"{BASE_URL}/analysis/{aid}", wait_for="h1")
            page.wait_for_timeout(3000)
            # 切换 tab
            for tab in ["归因分析", "情景回测"]:
                try:
                    btn = page.locator(f"button[role='tab']:has-text('{tab}')")
                    if btn.count() > 0:
                        btn.first.click()
                        page.wait_for_timeout(4000)
                        shot(page, f"06_analysis_tab_{tab}")
                        REPORT["ux_observations"].append(f"analysis: tab '{tab}' 切换 ✓")
                except Exception as e:
                    REPORT["issues"].append(f"analysis tab {tab}: {e}")

            # 截图核心 stats
            try:
                page.locator("button[role='tab']:has-text('统计概览')").first.click()
                page.wait_for_timeout(2000)
                shot(page, "06b_stats_tab")
            except Exception:
                pass

            # 尝试生成 AI 报告
            try:
                gen_btn = page.locator(
                    "button:has-text('生成 AI 报告'), button:has-text('查看 AI 报告')"
                )
                if gen_btn.count() > 0:
                    gen_btn.first.click()
                    # 等报告生成（可能耗时）
                    try:
                        page.wait_for_url("**/report/**", timeout=180000)
                        REPORT["ux_observations"].append(
                            f"report: 生成成功跳转 {page.url}"
                        )
                        page.wait_for_timeout(3000)
                        shot(page, "07_report")
                        # 收集报告主体
                        body = page.evaluate("() => document.body.innerText")
                        REPORT["ai_diagnostics"].append(
                            {"url": page.url, "body_excerpt": body[:1500]}
                        )
                    except PlaywrightTimeout:
                        shot(page, "07_report_timeout")
                        REPORT["issues"].append("report: 180s 内未跳转")
            except Exception as e:
                REPORT["issues"].append(f"generate report: {e}")
        else:
            REPORT["issues"].append("未成功上传任何文件，跳过 analysis/report")
            visit(page, "06_analysis_no_data", f"{BASE_URL}/analysis")

        # 7. History
        visit(page, "07_history", f"{BASE_URL}/history")
        try:
            link = page.locator("a[href*='/analysis/']")
            if link.count() > 0:
                href = link.first.get_attribute("href")
                REPORT["ux_observations"].append(f"history: 找到第一条记录 {href}")
                link.first.click()
                page.wait_for_timeout(3000)
                shot(page, "07b_history_first")
        except Exception as e:
            REPORT["issues"].append(f"history click: {e}")

        # 8. Admin
        visit(page, "08_admin", f"{BASE_URL}/admin")

        # 9. 404
        visit(page, "09_404", f"{BASE_URL}/this-page-does-not-exist")

        # 10. 移动端
        page.set_viewport_size({"width": 375, "height": 812})
        visit(page, "10_mobile_landing", f"{BASE_URL}/")
        # 移动端 upload
        if uploaded_analysis_ids:
            visit(page, "10b_mobile_analysis", f"{BASE_URL}/analysis/{uploaded_analysis_ids[-1]}")
        page.set_viewport_size({"width": 1440, "height": 900})

        browser.close()

    REPORT["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    out = os.path.join(OUTPUT_DIR, "audit_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=2)
    print(f"\n=== Audit Report ===")
    print(f"Saved: {out}")
    print(f"Pages: {len(REPORT['pages'])}, Console errors: {len(REPORT['console_errors'])}, "
          f"Network failures: {len(REPORT['network_failures'])}")
    print(f"Issues: {len(REPORT['issues'])}")
    for i in REPORT["issues"][:30]:
        print(f"  ! {i}")
    print(f"UX observations: {len(REPORT['ux_observations'])}")
    for o in REPORT["ux_observations"][:30]:
        print(f"  ✓ {o}")


if __name__ == "__main__":
    main()
