from pathlib import Path
import re

p = Path("frontend/src/components/AiSearchAnswer.jsx")
if p.exists():
    txt = p.read_text(encoding="utf-8")
    
    # 1. 壊れた関数シグネチャ部分をごっそり綺麗な状態にリセット
    txt = re.sub(
        r"export\s+default\s+function\s+AiSearchAnswer.*?\{",
        "export default function AiSearchAnswer({ query, filteredThreads, onOpenTopicDetail }) {",
        txt,
        flags=re.DOTALL
    )
    
    # 誤って挿入された変数宣言などのゴミを削除
    txt = re.sub(r"\s*const actualCityCode = [^;]+;", "", txt)
    txt = re.sub(r"\s*const activeCityCode = [^;]+;", "", txt)
    
    # 2. 複雑な条件分岐をやめ、全都市共通の「本議会」というスマートな表現に統一
    txt = re.sub(r"\{?[^}]*大阪市会において[^}]*\}?", "本議会において", txt)
    txt = re.sub(r"\{?[^}]*大阪市会[^}]*\}?", "本議会", txt)
    txt = txt.replace("京都市会において", "本議会において")
    txt = txt.replace("京都市議会において", "本議会において")
    txt = txt.replace("京都市会", "本議会")
    txt = txt.replace("京都市議会", "本議会")
    
    p.write_text(txt, encoding="utf-8")
    print("✅ AiSearchAnswer.jsx を修復し、全都市対応の「本議会」表記に統一しました。")
