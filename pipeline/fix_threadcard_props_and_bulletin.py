from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. SpeakerDetailView.jsx 内の ThreadCard 呼び出しと選管公報リンクを修正
# ==========================================
sdv_path = PROJECT_ROOT / "frontend" / "src" / "components" / "SpeakerDetailView.jsx"
sdv_text = sdv_path.read_text(encoding="utf-8")

# ① 選挙公報リンクの「京都市選管」を動的化
sdv_text = sdv_text.replace(
    "京都市選管 公式公報原本（PDF）で紙面を確認",
    "{cityCode === 'osaka' ? '大阪市選管 公式公報原本（PDF）で紙面を確認' : '京都市選管 公式公報原本（PDF）で紙面を確認'}"
)

# ② SpeakerDetailView 内で ThreadCard を呼んでいる箇所に cityCode={cityCode} を確実に付与
# パターン: <ThreadCard ... />
def inject_city_code(match):
    tag = match.group(0)
    if "cityCode=" in tag:
        return tag
    return tag.replace("<ThreadCard", "<ThreadCard\n                          cityCode={cityCode}")

sdv_text = re.sub(r"<ThreadCard\b[^>]*\/?>", inject_city_code, sdv_text)
sdv_path.write_text(sdv_text, encoding="utf-8")
print("✅ SpeakerDetailView.jsx の ThreadCard に cityCode を渡し、選管表記を修正しました。")

# ==========================================
# 2. 他の場所（SearchResultsView, MainTabView等）の ThreadCard も一括チェック
# ==========================================
for p in (PROJECT_ROOT / "frontend" / "src" / "components").glob("*.jsx"):
    txt = p.read_text(encoding="utf-8")
    if "<ThreadCard" in txt and "cityCode=" not in txt:
        # コンポーネント自身が cityCode を props またはスコープに持っているか確認
        if "cityCode" in txt:
            txt = re.sub(r"<ThreadCard\b(?![^>]*cityCode=)", "<ThreadCard cityCode={cityCode} ", txt)
            p.write_text(txt, encoding="utf-8")
            print(f"✅ {p.name} 内の ThreadCard 呼び出しに cityCode を追加しました。")

# ==========================================
# 3. ThreadCard.jsx 自体のフォールバック強化
# ==========================================
tc_path = PROJECT_ROOT / "frontend" / "src" / "components" / "ThreadCard.jsx"
tc_text = tc_path.read_text(encoding="utf-8")

# 会議名(committee_name/meeting_name)や council_id、自治体名に「大阪」があれば cityCode に関係なく大阪判定
detect_logic = """  // 自治体判定（props、council、URL、会議録タイトルに含まれる大阪/Kyotoから網羅的に判定）
  const item = typeof stmt !== 'undefined' ? stmt : (typeof thread !== 'undefined' ? thread : (typeof statement !== 'undefined' ? statement : {}));
  const isOsakaThread = cityCode === 'osaka' || 
                        item?.council === '大阪市会' || 
                        item?.council === '大阪市' ||
                        item?.city === 'osaka' ||
                        (typeof item?.meeting_name === 'string' && item.meeting_name.includes('大阪市')) ||
                        (typeof item?.committee_name === 'string' && item.committee_name.includes('大阪市')) ||
                        (typeof item?.source_url === 'string' && item.source_url.includes('city.osaka.lg.jp'));
  const councilOriginalLabel = isOsakaThread ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認';"""

tc_text = re.sub(
    r"// 自治体判定.*?const councilOriginalLabel = .*?;",
    detect_logic,
    tc_text,
    flags=re.DOTALL
)
# 既存の判定コメント構造へのフォールバック置換
tc_text = re.sub(
    r"const item = typeof stmt.*?const councilOriginalLabel = .*?;",
    detect_logic,
    tc_text,
    flags=re.DOTALL
)

tc_path.write_text(tc_text, encoding="utf-8")
print("✅ ThreadCard.jsx の自動判定ロジックを強化しました。")
