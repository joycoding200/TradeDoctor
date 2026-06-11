"""
API Contract Tests — verify backend response shapes match frontend expectations.
No browser needed. These are fast, deterministic, and should run in CI.

Usage:
    python e2e/api_contract_tests.py
    # Assumes backend is running on http://localhost:8000
"""

import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0


def api(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except json.JSONDecodeError:
            return e.code, {"error": "empty response"}


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def register_and_login(email="ct_test@e2e.com"):
    """Helper: register + login, return token."""
    status, data = api("POST", "/api/auth/register", {"email": email, "password": "test123456"})
    if status not in (201, 409):
        return None
    status, data = api("POST", "/api/auth/login", {"email": email, "password": "test123456"})
    return data.get("access_token") if status == 200 else None


# ─── Auth Contract ───────────────────────────────────────────
section("Auth API Contract")

token = None
import time as _time
test_email = f"ct_{int(_time.time())}@e2e.com"
status, data = api("POST", "/api/auth/register", {"email": test_email, "password": "pass123456"})
check(status == 201, f"register returns 201 (got {status})")
check("access_token" in data, f"register has access_token: {'access_token' in data}")
check("token_type" in data, f"register has token_type: {'token_type' in data}")
check(data.get("token_type") == "bearer", f"token_type is bearer: {data.get('token_type')}")
token = data.get("access_token")
check(len(token) > 20 if token else False, f"token length > 20: {len(token) if token else 0}")

status, data = api("POST", "/api/auth/login", {"email": test_email, "password": "pass123456"})
check(status == 200, f"login returns 200 (got {status})")
check("access_token" in data, f"login returns access_token")
token = data.get("access_token")

status, data = api("POST", "/api/auth/register", {"email": "bad_email", "password": "123"})
check(status == 422, f"invalid email returns 422 (got {status})")

status, data = api("POST", "/api/auth/register", {"email": "x@test.com", "password": "12"})
check(status == 400, f"short password returns 400 (got {status})")


# ─── Upload Contract ─────────────────────────────────────────
section("Upload API Contract")

if not token:
    print("  [FAIL] No token, skipping upload tests")
    sys.exit(1)

# Upload CSV
csv_content = "委托时间,证券代码,买卖方向,成交价格,成交数量\n2026-01-05 09:35:00,600519,买入,1500.00,100\n2026-01-10 14:20:00,600519,卖出,1520.00,100\n"
import io

# Use requests-style multipart for upload
boundary = "----TestBoundary"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="trades.csv"\r\n'
    f"Content-Type: text/csv\r\n\r\n"
    f"{csv_content}\r\n"
    f"--{boundary}--\r\n"
).encode()

req = urllib.request.Request(f"{BASE}/api/upload", data=body, method="POST")
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
req.add_header("Authorization", f"Bearer {token}")
try:
    with urllib.request.urlopen(req) as resp:
        upload_data = json.loads(resp.read())
        status = resp.status
except urllib.error.HTTPError as e:
    status = e.code
    upload_data = json.loads(e.read())

check(status in (200, 201), f"upload returns 200/201 (got {status})")
check("raw_file_id" in upload_data, f"upload has raw_file_id: {'raw_file_id' in upload_data}")
check("detected_formats" in upload_data, f"upload has detected_formats: {'detected_formats' in upload_data}")

formats = upload_data.get("detected_formats", [])
check(isinstance(formats, list), f"detected_formats is list: {isinstance(formats, list)}")
if formats:
    f0 = formats[0]
    check("source_type" in f0, f"format has source_type: {'source_type' in f0}")
    check("asset_type" in f0, f"format has asset_type: {'asset_type' in f0}")
    check("score" in f0, f"format has score: {'score' in f0}")
    check(isinstance(f0.get("score"), (int, float)), f"score is number: {type(f0.get('score')).__name__}")

raw_id = upload_data.get("raw_file_id", "")
check(len(raw_id) > 0, f"raw_file_id is non-empty: {len(raw_id) > 0}")

# Confirm format
status, confirm_data = api("POST", "/api/upload/confirm", {"raw_file_id": raw_id, "source_type": "qmt"}, token)
check(status in (200, 201), f"confirm returns 200/201 (got {status})")
check("trades" in confirm_data, f"confirm has trades: {'trades' in confirm_data}")
check("count" in confirm_data, f"confirm has count: {'count' in confirm_data}")

trades = confirm_data.get("trades", [])
check(isinstance(trades, list) and len(trades) > 0, f"trades is non-empty list: {isinstance(trades, list) and len(trades)}")
if trades:
    t = trades[0]
    for field in ["symbol", "side", "quantity", "price", "datetime", "exchange"]:
        check(field in t, f"trade has {field}: {field in t}")

# Import
status, import_data = api("POST", "/api/upload/import", {"raw_file_id": raw_id}, token)
check(status in (200, 201), f"import returns 200/201 (got {status})")
check("imported_count" in import_data, f"import has imported_count: {'imported_count' in import_data}")
check(import_data.get("imported_count", 0) > 0, f"imported_count > 0: {import_data.get('imported_count')}")


# ─── Analysis Contract ───────────────────────────────────────
section("Analysis API Contract")

status, run_data = api("POST", "/api/analysis/run", {"date_start": "2020-01-01", "date_end": "2026-12-31"}, token)
check(status in (200, 201), f"run analysis returns 200/201 (got {status})")
check("analysis_id" in run_data, f"run has analysis_id: {'analysis_id' in run_data}")

aid = run_data.get("analysis_id", "")

# Stats
status, stats = api("GET", f"/api/analysis/{aid}/stats", token=token)
check(status == 200, f"stats returns 200 (got {status})")
for field in ["total_trades", "total_positions", "win_count", "win_rate", "total_pnl", "avg_holding_days", "positions"]:
    check(field in stats, f"stats has {field}: {field in stats}")
check(isinstance(stats.get("win_rate"), (int, float)), f"win_rate is number")
check(0 <= stats.get("win_rate", -1) <= 1, f"win_rate in [0,1]: {stats.get('win_rate')}")

# Insight
status, insight = api("GET", f"/api/analysis/{aid}/insight", token=token)
check(status == 200, f"insight returns 200 (got {status})")
check("patterns" in insight, f"insight has patterns: {'patterns' in insight}")
check("best_pattern" in insight, f"insight has best_pattern: {'best_pattern' in insight}")
check("worst_pattern" in insight, f"insight has worst_pattern: {'worst_pattern' in insight}")
if insight.get("patterns"):
    p = insight["patterns"][0]
    for field in ["pattern_name", "count", "win_count", "win_rate", "total_pnl", "avg_pnl_pct"]:
        check(field in p, f"pattern item has {field}: {field in p}")

# What If
status, whatif = api("GET", f"/api/analysis/{aid}/whatif", token=token)
check(status == 200, f"whatif returns 200 (got {status})")
check("items" in whatif, f"whatif has items: {'items' in whatif}")
if whatif.get("items"):
    item = whatif["items"][0]
    for field in ["removed_pattern", "original_return", "what_if_return", "delta", "impact_score"]:
        check(field in item, f"whatif item has {field}: {field in item}")


# ─── Report Contract ─────────────────────────────────────────
section("Report API Contract")

# Report generation requires mock LLM in test - skip if OPENAI_API_KEY not set
status, gen_data = api("POST", "/api/report/generate", {"analysis_id": aid}, token)
if status == 200 or status == 201:
    check("report_id" in gen_data, f"generate has report_id: {'report_id' in gen_data}")
    rid = gen_data.get("report_id", "")

    status, report = api("GET", f"/api/report/{rid}", token=token)
    check(status == 200, f"get report returns 200 (got {status})")
    if status == 200:
        for field in ["id", "report_content", "validation_passed", "ai_provider", "created_at"]:
            check(field in report, f"report has {field}: {field in report}")

    status, reports = api("GET", "/api/reports", token=token)
    check(status == 200, f"list reports returns 200 (got {status})")
    check("reports" in reports, f"list has reports: {'reports' in reports}")
    check("total" in reports, f"list has total: {'total' in reports}")
else:
    print(f"  [WARN] Report generation returned {status} (likely needs OPENAI_API_KEY)")

# ─── Cross-User Isolation ────────────────────────────────────
section("Cross-User Isolation")

token2 = register_and_login("other_user@e2e.com")
if token2:
    status, data = api("GET", f"/api/analysis/{aid}/stats", token=token2)
    check(status == 404, f"user2 cannot access user1 analysis: {status} (expected 404)")


# ─── Summary ─────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
print(f"{'='*60}")

if FAIL > 0:
    print("\n*** CONTRACT TESTS FAILED ***")
    sys.exit(1)
else:
    print("\n*** ALL CONTRACT TESTS PASSED ***")
