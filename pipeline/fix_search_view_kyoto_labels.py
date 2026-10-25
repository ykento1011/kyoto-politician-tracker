from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. AiSearchAnswer.jsx の「京都市議会 / 京都市会」を動的化
# ==========================================
ai_path = PROJECT_ROOT / "frontend" / "src" / "components" / "AiSearchAnswer.jsx"
if ai_path.exists():
    ai_text = ai_path.read_text(encoding="utf-8")
    
    # 引数 props に cityCode を確実に持たせる
    if "cityCode" not in ai_text.split("export default function")[1].split("{")[0]:
        ai_text = re.sub(
            r"export default function AiSearchAnswer\(\{([^}]+)\}\)",
            r"export default function AiSearchAnswer({\1, cityCode = 'kyoto'})",
            ai_text
        )

    # 「京都市議会において」「京都市会において」を動的化
    ai_text = ai_text.replace("京都市議会において", "{cityCode === 'osaka' ? '大阪市会において' : '京都市議会において'}")
    ai_text = ai_text.replace("京都市会において", "{cityCode === 'osaka' ? '大阪市会において' : '京都市会において'}")
    ai_text = ai_text.replace("京都市議会", "{cityCode === 'osaka' ? '大阪市会' : '京都市議会'}")
    
    ai_path.write_text(ai_text, encoding="utf-8")
    print("✅ AiSearchAnswer.jsx の市会表記を修正しました。")

# ==========================================
# 2. 検索結果を表示する各ビュー（SearchResultsView, TopicDetailPage 等）で
#    ThreadCard に cityCode={cityCode} を確実に注入
# ==========================================
components_dir = PROJECT_ROOT / "frontend" / "src" / "components"
for p in components_dir.glob("*.jsx"):
    txt = p.read_text(encoding="utf-8")
    modified = False

    # AiSearchAnswer 呼び出しに cityCode を付与
    if "<AiSearchAnswer" in txt and "cityCode=" not in txt.split("<AiSearchAnswer")[1].split("/>")[0]:
        txt = txt.replace("<AiSearchAnswer", "<AiSearchAnswer cityCode={cityCode}")
        modified = True

    # ThreadCard 呼び出しに cityCode を付与
    if "<ThreadCard" in txt:
        # cityCode= が含まれていない呼び出し箇所を置換
        def inject_city(m):
            tag = m.group(0)
            if "cityCode=" in tag:
                return tag
            return tag.replace("<ThreadCard", "<ThreadCard cityCode={cityCode}")
        
        new_txt = re.sub(r"<ThreadCard\b[^>]*\/?>", inject_city, txt)
        if new_txt != txt:
            txt = new_txt
            modified = True

    # 静的な「京都市会 公式原本で確認」がまだ直書きされている場合は置換
    if "京都市会 公式原本で確認" in txt:
        txt = txt.replace(
            "京都市会 公式原本で確認",
            "{cityCode === 'osaka' ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認'}"
        )
        modified = True

    if modified:
        p.write_text(txt, encoding="utf-8")
        print(f"✅ {p.name} 内の cityCode 連携および原本ラベルを更新しました。")

# ==========================================
# 3. ThreadCard.jsx 自体のフォールバック（判定漏れ防止）
# ==========================================
tc_path = components_dir / "ThreadCard.jsx"
if tc_path.exists():
    tc_text = tc_path.read_text(encoding="utf-8")
    
    # URL や window.location からの確実な大阪判定を最優先ガードとして追加
    guard_logic = """  // URLパス または props/データから大阪を直接判定
  const isOsakaUrl = typeof window !== 'undefined' && window.location.pathname.startsWith('/osaka');
  const isOsakaThread = isOsakaUrl || 
                        cityCode === 'osaka' || 
                        stmt?.council === '大阪市会' || 
                        stmt?.council === '大阪市' ||
                        thread?.council === '大阪市会' ||
                        (typeof stmt?.meeting_name === 'string' && stmt.meeting_name.includes('大阪市')) ||
                        (typeof thread?.meeting_name === 'string' && thread.meeting_name.includes('大阪市')) ||
                        (typeof stmt?.committee_name === 'string' && stmt.committee_name.includes('大阪市')) ||
                        (typeof thread?.committee_name === 'string' && thread.committee_name.includes('大阪市'));
  const councilOriginalLabel = isOsakaThread ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認';"""

    tc_text = re.sub(
        r"// 自治体判定.*?const councilOriginalLabel = .*?;",
        guard_logic,
        tc_text,
        flags=re.DOTALL
    )
    tc_path.write_text(tc_text, encoding="utf-8")
    print("✅ ThreadCard.jsx のURLベース自動判定ガードを適用しました。")
