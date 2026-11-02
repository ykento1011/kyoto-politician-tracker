import json
from pathlib import Path
import re
import sys

BASE_DIR = Path(__file__).parent.resolve()
ROOT = BASE_DIR.parent
DATA_DIR = ROOT / "frontend" / "public" / "data"

def clean(s):
    return re.sub(r"[\s\u3000\r\n\t]+", "", str(s or ""))

def main():
    print("=" * 80)
    print(" 🛡️ 全自動インテグリティ監査（5都市 モーダル到達率＆発言データ健全性）")
    print("=" * 80)

    city_configs = [
        ("KYOTO", "kyoto_topic_summaries.json", "timelines", "kyoto_statements_summary.json"),
        ("OSAKA", "osaka_topic_summaries.json", "osaka_timelines", "osaka_statements_summary.json"),
        ("NAGOYA", "nagoya_topic_summaries.json", "nagoya_timelines", "nagoya_statements_summary.json"),
        ("YOKOHAMA", "yokohama_topic_summaries.json", "yokohama_timelines", "yokohama_statements_summary.json"),
        ("KOBE", "kobe_topic_summaries.json", "kobe_timelines", "kobe_statements_summary.json")
    ]

    audit_results = []
    all_pass = True

    for city_name, topic_file, tl_dir_name, summary_file in city_configs:
        t_path = DATA_DIR / topic_file
        tl_d = DATA_DIR / tl_dir_name
        s_path = DATA_DIR / summary_file
        
        if not t_path.exists():
            continue
            
        # フロントエンドと同様、statements_summary から逆引きインデックスを構築
        lookup = {}
        if s_path.exists():
            try:
                s_data = json.loads(s_path.read_text(encoding="utf-8"))
                statements = s_data.get("statements", []) if isinstance(s_data, dict) else s_data
                for s in statements:
                    m_date = s.get("meeting_date")
                    spk = clean(s.get("speaker"))
                    mid = s.get("meeting_id")
                    seq = str(s.get("sequence_number") or "")
                    if m_date and spk and mid:
                        key = (m_date, spk)
                        if key not in lookup:
                            lookup[key] = []
                        lookup[key].append((mid, seq))
            except Exception:
                pass

        topics = json.loads(t_path.read_text(encoding="utf-8"))

        city_total = 0
        modal_ok = 0
        speech_ok = 0

        for topic in topics:
            for phase in topic.get("timeline_phases", []):
                for ex in phase.get("exchanges", []):
                    city_total += 1
                    mid = ex.get("meeting_id")
                    seq = str(ex.get("sequence_number") or "")
                    spk = clean(ex.get("speaker"))
                    m_date = ex.get("meeting_date")
                    text = ex.get("statement_summary", "")

                    # 直接 mid がない場合はフロントエンドと同様に逆引き解決
                    if not mid and m_date and spk:
                        matches = lookup.get((m_date, spk), [])
                        if matches:
                            mid, seq = matches[0]

                    # モーダル到達検証: タイムラインJSONの存在確認（または公式原本リンク）
                    if mid and tl_d.exists():
                        tl_file = tl_d / f"{mid}.json"
                        if tl_file.exists():
                            modal_ok += 1
                    elif ex.get("official_url"):
                        # 神戸等の外部一次情報直接リンク対応
                        modal_ok += 1

                    # 発言内容の健全性チェック（テキストが空でなく、有効な発言内容を保持しているか）
                    if text and len(str(text).strip()) >= 5:
                        speech_ok += 1

        audit_results.append({
            "city": city_name,
            "total": city_total,
            "modal_ok": modal_ok,
            "speech_ok": speech_ok
        })

    print(f"\n{'都市':<8} | {'総カード数':<10} | {'モーダル到達率':<14} | {'発言データ健全性':<14} | 判定")
    print("-" * 75)

    for r in audit_results:
        if r["total"] == 0:
            status = "ℹ️ PREP"
            print(f"{r['city']:<8} | {r['total']:<10} | {'--.-% (準備中)':>16} | {'--.-% (準備中)':>16} | {status}")
            continue

        modal_pct = (r["modal_ok"] / r["total"] * 100) if r["total"] > 0 else 0
        speech_pct = (r["speech_ok"] / r["total"] * 100) if r["total"] > 0 else 0
        status = "✅ PASS" if modal_pct >= 98.0 and speech_pct >= 90.0 else "⚠️ CHECK"
        if status != "✅ PASS":
            all_pass = False
        print(f"{r['city']:<8} | {r['total']:<10} | {modal_pct:>6.1f}% ({r['modal_ok']}/{r['total']}) | {speech_pct:>6.1f}% ({r['speech_ok']}/{r['total']}) | {status}")

    if all_pass:
        print("\n🎉 ALL PASS: 稼働中全都市でモーダル到達率 98%以上・発言データ健全性 90%以上を達成しました！")
        sys.exit(0)
    else:
        print("\n❌ FAILED: インテグリティ監査に不合格の都市があります。")
        sys.exit(1)

if __name__ == "__main__":
    main()
