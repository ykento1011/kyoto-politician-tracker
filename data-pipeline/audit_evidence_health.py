import os
import sys
import json
import time
import random
import argparse
import urllib.parse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import requests

# 自己署名証明書や中間証明書の警告を抑制
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, "frontend", "public", "data")
QUEUE_DIR = os.path.join(BASE_DIR, "data")
QUEUE_FILE = os.path.join(QUEUE_DIR, "evidence_health_queue.json")

CITIES = ["kyoto", "osaka", "nagoya", "yokohama", "kobe"]
USER_AGENT = "GikaiNoMikata-HealthChecker/1.0 (+https://gikai-mikata.jp)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
}

def collect_targets(cities, test_mock_404=False):
    targets = []
    for city in cities:
        json_path = os.path.join(FRONTEND_DATA_DIR, f"{city}_mayor_tracker.json")
        if not os.path.exists(json_path):
            continue
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ JSON読込失敗: {json_path} ({e})")
            continue

        mayor_info = data.get("mayor_info", {})
        # mayor_info 内のURL
        for field in ["bulletin_pdf", "strategy_main_pdf", "strategy_policy_pdf"]:
            url = mayor_info.get(field)
            if url and isinstance(url, str) and url.startswith("http"):
                targets.append({
                    "city": city,
                    "pledge_id": "mayor_info",
                    "headline": mayor_info.get("name", "首長基本公文書"),
                    "field": f"mayor_info.{field}",
                    "url": url
                })

        # pledges 内のURL
        for p in data.get("pledges", []):
            pid = p.get("pledge_id", "unknown")
            hl = p.get("headline", "—")

            # ① election_promise.bulletin_url
            ep_url = p.get("election_promise", {}).get("bulletin_url")
            if ep_url and isinstance(ep_url, str) and ep_url.startswith("http"):
                targets.append({
                    "city": city,
                    "pledge_id": pid,
                    "headline": hl,
                    "field": "election_promise.bulletin_url",
                    "url": ep_url
                })

            # ② official_plan.doc_url
            op_url = p.get("official_plan", {}).get("doc_url")
            if op_url and isinstance(op_url, str) and op_url.startswith("http"):
                targets.append({
                    "city": city,
                    "pledge_id": pid,
                    "headline": hl,
                    "field": "official_plan.doc_url",
                    "url": op_url
                })

            # ③ budget_records[].doc_url
            for idx, b in enumerate(p.get("budget_records", [])):
                b_url = b.get("doc_url")
                if b_url and isinstance(b_url, str) and b_url.startswith("http"):
                    targets.append({
                        "city": city,
                        "pledge_id": pid,
                        "headline": hl,
                        "field": f"budget_records[{idx}].doc_url",
                        "url": b_url
                    })

            # ④ ordinance_records[].doc_url
            for idx, o in enumerate(p.get("ordinance_records", [])):
                o_url = o.get("doc_url")
                if o_url and isinstance(o_url, str) and o_url.startswith("http"):
                    targets.append({
                        "city": city,
                        "pledge_id": pid,
                        "headline": hl,
                        "field": f"ordinance_records[{idx}].doc_url",
                        "url": o_url
                    })

            # ⑤ milestone.evidence_url
            ms_url = p.get("milestone", {}).get("evidence_url")
            if ms_url and isinstance(ms_url, str) and ms_url.startswith("http"):
                targets.append({
                    "city": city,
                    "pledge_id": pid,
                    "headline": hl,
                    "field": "milestone.evidence_url",
                    "url": ms_url
                })

    if test_mock_404:
        targets.append({
            "city": "kyoto",
            "pledge_id": "TEST_999",
            "headline": "【テスト用モック施策】",
            "field": "milestone.evidence_url",
            "url": "https://www.city.kyoto.lg.jp/mock_test_404_not_found_page.html",
            "is_mock_404": True
        })

    return targets

def check_single_url(target_item, timeout=(3.0, 5.0)):
    url = target_item["url"]

    # テスト用モック404
    if target_item.get("is_mock_404"):
        return {
            **target_item,
            "status_code": 404,
            "ok": False,
            "method": "MOCK",
            "error": "Intentional Test 404 Not Found"
        }

    # ドメイン単位の過負荷・WAF検知防止ランダムジッター（100〜250ms）
    time.sleep(random.uniform(0.1, 0.25))

    # 1. HEADリクエスト
    try:
        resp = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True, verify=False)
        if resp.status_code in [403, 405, 501]:
            raise requests.RequestException(f"HEAD status {resp.status_code}, fallback to GET")
        is_ok = (200 <= resp.status_code < 400)
        return {
            **target_item,
            "status_code": resp.status_code,
            "ok": is_ok,
            "method": "HEAD",
            "error": None if is_ok else f"HTTP {resp.status_code}"
        }
    except Exception as e_head:
        # 2. 軽量GETフォールバック (Range: 0-1024, stream=True)
        try:
            get_headers = HEADERS.copy()
            get_headers["Range"] = "bytes=0-1024"
            resp = requests.get(url, headers=get_headers, timeout=timeout, allow_redirects=True, stream=True, verify=False)
            status = resp.status_code
            resp.close()
            is_ok = (200 <= status < 400) or (status == 206)
            return {
                **target_item,
                "status_code": status,
                "ok": is_ok,
                "method": "GET_STREAM",
                "error": None if is_ok else f"HTTP {status}"
            }
        except Exception as e_get:
            return {
                **target_item,
                "status_code": 0,
                "ok": False,
                "method": "FAILED",
                "error": str(e_get)
            }

def save_to_queue(failed_items):
    os.makedirs(QUEUE_DIR, exist_ok=True)
    existing = []
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    queue_map = {f"{item['city']}_{item['field']}_{item['url']}": item for item in existing}
    now_str = datetime.now().isoformat()
    for item in failed_items:
        key = f"{item['city']}_{item['field']}_{item['url']}"
        rec = {
            "city": item["city"],
            "pledge_id": item["pledge_id"],
            "headline": item["headline"],
            "field": item["field"],
            "url": item["url"],
            "status_code": item.get("status_code", 0),
            "method": item.get("method", "UNKNOWN"),
            "error": item.get("error", "Error"),
            "detected_at": now_str
        }
        queue_map[key] = rec

    updated_list = list(queue_map.values())
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_list, f, ensure_ascii=False, indent=2)
    return len(failed_items)

def main():
    parser = argparse.ArgumentParser(description="首長政策トラッカー 一次公文書エビデンス死活監視")
    parser.add_argument("--city", default="all", help="検査対象都市 (kyoto, osaka, nagoya, yokohama, kobe, all)")
    parser.add_argument("--queue-only", action="store_true", help="非ブロッキングモード（エラー検知時も exit 0 で終了しキューに退避）")
    parser.add_argument("--strict", action="store_true", help="厳格モード（1件でもエラーがあれば exit 1）")
    parser.add_argument("--workers", type=int, default=6, help="並行リクエストワーカー数 (デフォルト: 6)")
    parser.add_argument("--test-mock-404", action="store_true", help="テスト用モック404 URLを混入させて検証")
    args = parser.parse_args()

    target_cities = CITIES if args.city == "all" else [args.city]
    targets = collect_targets(target_cities, test_mock_404=args.test_mock_404)

    print("=" * 75)
    print(f" 🛡️ 一次公文書エビデンス死活監視（Health Check）開始")
    print(f" 📊 対象都市: {', '.join(target_cities)} | 検査対象URL総数: {len(targets)} 件 | Workers: {args.workers}")
    print("=" * 75)

    start_time = time.time()
    passed = []
    failed = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(check_single_url, t): t for t in targets}
        for future in as_completed(futures):
            res = future.result()
            if res["ok"]:
                passed.append(res)
            else:
                failed.append(res)
                print(f" ❌ [FAIL {res['status_code']}] [{res['city'].upper()}] {res['headline'][:24]}... ({res['field']})")
                print(f"    URL: {res['url']}")
                print(f"    Error: {res['error']}")

    elapsed = time.time() - start_time

    print("-" * 75)
    print(f" ⏱️ 検査完了 所要時間: {elapsed:.2f} 秒")
    print(f" ✅ 通過（HTTP 200/206等）: {len(passed)} 件 / {len(targets)} 件")
    print(f" ⚠️ 異常（要調査キュー行き）: {len(failed)} 件")
    print("-" * 75)

    if failed:
        q_count = save_to_queue(failed)
        print(f" 📝 異常検知URLを要調査キューに退避しました: {QUEUE_FILE} ({q_count} 件)")
        if args.strict:
            print(" 🚨 --strict モードのため終了コード 1 を返します。")
            sys.exit(1)
        else:
            print(" 🛡️ --queue-only モードのため安全に終了コード 0 を返します（非ブロッキング）。")
            sys.exit(0)
    else:
        print(" 🎉 全URLが正常（HTTP 200）に疎通しました。")
        sys.exit(0)

if __name__ == "__main__":
    main()
