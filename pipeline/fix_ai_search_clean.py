from pathlib import Path

p = Path("frontend/src/components/AiSearchAnswer.jsx")
if p.exists():
    lines = p.read_text(encoding="utf-8").splitlines()
    new_lines = []
    
    for line in lines:
        # 関数定義の行を検知して、まるごと綺麗な1行に置き換える
        if line.startswith("export default function AiSearchAnswer"):
            new_lines.append("export default function AiSearchAnswer({ query, filteredThreads, onOpenTopicDetail }) {")
        else:
            new_lines.append(line)
            
    p.write_text("\n".join(new_lines), encoding="utf-8")
    print("✅ AiSearchAnswer.jsx のシグネチャ行を完全にクリーンアップしました。")
