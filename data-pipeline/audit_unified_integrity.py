import json
from pathlib import Path
import re
import sys

BASE_DIR = Path(__file__).parent.resolve()
ROOT = BASE_DIR.parent
DATA_DIR = ROOT / "frontend" / "public" / "data"

def clean(s):
    return re.sub(r"[\s\u3000\r\n\t、。・「」『』（）()…\.]+", "", str(s or ""))

def main():
    print("================================================================================")
    print(" 🛡️ 全自動インテグリティ監査（京都・大阪・名古屋 モーダル到達率＆生発言率）")
    print("================================================================================")

    city_configs = [
        ("KYOTO", "topic_summaries.json", "timelines"),
        ("OSAKA", "osaka_topic_summaries.json", "osaka_timelines"),
        ("NAGOYA", "nagoya_topic_summaries.json", "nagoya_timelines"),
        ("YOKOHAMA", "yokohama_topic_summaries.json", "yokohama_timelines")
    ]

    audit_results = []
    all_pass = True

    for city_name, topic_file, tl_dir_name in city_configs:
        t_path = DATA_DIR / topic_file
        tl_d = DATA_DIR / tl_dir_name
        
        if not t_path.exists():
            continue
            
        topics = json.loads(t_path.read_text(encoding="utf-8"))

        city_total = 0
        modal_ok = 0
        speech_ok = 0

        for topic in topics:
            for phase in topic.get("timeline_phases", []):
                for ex in phase.get("exchanges", []):
                    city_total += 1
                    mid = str(ex.get("meeting_id") or "")
                    seq = str(ex.get("sequence_number") or "")
                    spk = ex.get("speaker", "")
                    text = ex.get("statement_summary", "")

                    tl_file = tl_d / f"{mid}.json"
                    if tl_file.exists():
                        try:
                            tl_data = json.loads(tl_file.read_text(encoding="utf-8"))
                            if seq in tl_data or any(clean(spk) in clean(m.get("speaker", "")) for msgs in tl_data.values() if isinstance(msgs, list) for m in msgs):
                                modal_ok += 1
                        except Exception:
                            pass

                    # 三人称要約でなく肉声かチェック
                    if not any(re.search(p, text) for p in [r"議員(は|が|も)", r"(質問|質疑|見解|説明|答弁)を(行い|求め|行われ|した)", r"(説明|答弁|言及|報告)した[。、]"]):
                        speech_ok += 1

        audit_results.append({
            "city": city_name,
            "total": city_total,
            "modal_ok": modal_ok,
            "speech_ok": speech_ok
        })

    print(f"\n{'都市':<8} | {'総カード数':<10} | {'モーダル到達率':<14} | {'生発言率 (肉声)':<14} | 判定")
    print("-" * 65)

    for r in audit_results:
        if r["total"] == 0:
            status = "ℹ️ PREP"
            print(f"{r['city']:<8} | {r['total']:<10} | {'--.-% (準備中)':>16} | {'--.-% (準備中)':>16} | {status}")
            continue

        modal_pct = (r["modal_ok"] / r["total"] * 100)
        speech_pct = (r["speech_ok"] / r["total"] * 100)
        status = "✅ PASS" if modal_pct >= 98 and speech_pct >= 90 else "⚠️ CHECK"
        if status != "✅ PASS":
            all_pass = False
        print(f"{r['city']:<8} | {r['total']:<10} | {modal_pct:>6.1f}% ({r['modal_ok']}/{r['total']}) | {speech_pct:>6.1f}% ({r['speech_ok']}/{r['total']}) | {status}")

    if all_pass:
        print("\n🎉 ALL PASS: 稼働中全都市でモーダル到達率 98%以上・生発言率 90%以上を達成しました！")
        sys.exit(0)
    else:
        print("\n❌ FAILED: インテグリティ監査に不合格の都市があります。")
        sys.exit(1)

if __name__ == "__main__":
    main()
