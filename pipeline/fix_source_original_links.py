from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. TopicDetailPage.jsx の原本リンク修正
# ==========================================
tdp_path = PROJECT_ROOT / "frontend" / "src" / "components" / "TopicDetailPage.jsx"
tdp_text = tdp_path.read_text(encoding="utf-8")

old_tdp = "<span>京都市会 公式原本で確認</span>"
new_tdp = "<span>{cityCode === 'osaka' ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認'}</span>"

if old_tdp in tdp_text:
    tdp_text = tdp_text.replace(old_tdp, new_tdp)
    tdp_path.write_text(tdp_text, encoding="utf-8")
    print("✅ TopicDetailPage.jsx の原本リンクを動的化しました。")
else:
    print("⚠️ TopicDetailPage.jsx に該当テキストが見つかりませんでした。")

# ==========================================
# 2. ThreadCard.jsx の原本リンク修正
# ==========================================
tc_path = PROJECT_ROOT / "frontend" / "src" / "components" / "ThreadCard.jsx"
tc_text = tc_path.read_text(encoding="utf-8")

# 引数 props に cityCode を受け取れるようにする（デフォルトは 'kyoto'）
if "cityCode" not in tc_text.split("export default function ThreadCard")[1].split("{")[0]:
    tc_text = re.sub(
        r"export default function ThreadCard\(\{([^}]+)\}\)",
        r"export default function ThreadCard({\1, cityCode})",
        tc_text
    )

# スレッド自身の council 属性、URL、または渡された cityCode から判定
# 大阪市会のURLには city.osaka.lg.jp が含まれるか、cityCode === 'osaka'
thread_city_check = """
  // 都市の判定（propsのcityCode、またはスレッド情報のcouncil/URLから動的判定）
  const isOsakaThread = cityCode === 'osaka' || 
                        thread?.council === '大阪市会' || 
                        thread?.source_url?.includes('city.osaka.lg.jp');
  const councilOriginalLabel = isOsakaThread ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認';
"""

# 関数先頭に判定ロジックを挿入
if "const isOsakaThread =" not in tc_text:
    tc_text = re.sub(
        r"(export default function ThreadCard\([^)]*\)\s*\{)",
        r"\1" + thread_city_check,
        tc_text
    )

# テキスト表示部分を置換
old_tc_label = "<span>京都市会 公式原本で確認</span>"
new_tc_label = "<span>{councilOriginalLabel}</span>"
if old_tc_label in tc_text:
    tc_text = tc_text.replace(old_tc_label, new_tc_label)
    tc_path.write_text(tc_text, encoding="utf-8")
    print("✅ ThreadCard.jsx の原本リンクを動的化しました。")
else:
    # 正規表現での置換フォールバック
    tc_text = re.sub(r"<span>京都市会\s*公式原本で確認</span>", new_tc_label, tc_text)
    tc_path.write_text(tc_text, encoding="utf-8")
    print("✅ ThreadCard.jsx の原本リンクを正規表現で動的化しました。")

print("完了")
